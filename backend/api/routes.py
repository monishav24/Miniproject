from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from backend.database.connection import get_session
from backend.database.models import User, Vehicle, Telemetry
from backend.api.auth import (
    get_password_hash, 
    verify_password, 
    create_access_token, 
    get_current_user
)

router = APIRouter()

# --- Schemas ---
class UserRegister(BaseModel):
    username: str
    password: str
    primary_vehicle_name: str

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class VehicleBase(BaseModel):
    name: str
    vin: Optional[str] = None

class VehicleCreate(VehicleBase):
    pass

class TelemetryCreate(BaseModel):
    vehicle_id: int
    latitude: float
    longitude: float
    speed: float
    heading: float

class TelemetryLive(TelemetryCreate):
    acceleration: float
    gyro: float

class TelemetryOut(TelemetryCreate):
    id: int
    timestamp: datetime
    collision_probability: float
    unsafe_score: float
    class Config:
        from_attributes = True

class VehicleOut(VehicleBase):
    id: int
    created_at: datetime
    last_telemetry: Optional[TelemetryOut] = None
    class Config:
        from_attributes = True

class VehicleStats(BaseModel):
    vehicle_count: int
    total_telemetry: int
    avg_unsafe_score: float
    last_communication: Optional[datetime]

# --- Auth Routes ---
@router.post("/auth/register", response_model=Token)
async def register(user_data: UserRegister, db: AsyncSession = Depends(get_session)):
    # Check if user exists
    result = await db.execute(select(User).where(User.username == user_data.username))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Username already registered")
    
    # Create user
    new_user = User(
        username=user_data.username,
        password_hash=get_password_hash(user_data.password)
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    # Create primary vehicle
    primary_vehicle = Vehicle(
        name=user_data.primary_vehicle_name,
        owner_id=new_user.id
    )
    db.add(primary_vehicle)
    await db.commit()
    
    access_token = create_access_token(data={"sub": new_user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/auth/login", response_model=Token)
async def login(user_data: UserLogin, db: AsyncSession = Depends(get_session)):
    result = await db.execute(select(User).where(User.username == user_data.username))
    user = result.scalars().first()
    
    if not user or not verify_password(user_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

# --- Vehicle Routes ---
@router.get("/vehicles", response_model=List[VehicleOut])
async def get_vehicles(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    result = await db.execute(select(Vehicle).where(Vehicle.owner_id == current_user.id))
    vehicles = result.scalars().all()
    
    vehicle_list = []
    for v in vehicles:
        # Get latest telemetry
        t_result = await db.execute(
            select(Telemetry)
            .where(Telemetry.vehicle_id == v.id)
            .order_by(Telemetry.timestamp.desc())
            .limit(1)
        )
        last_t = t_result.scalars().first()
        
        # Pydantic will handle the conversion
        v_out = VehicleOut.model_validate(v)
        if last_t:
            v_out.last_telemetry = TelemetryOut.model_validate(last_t)
        vehicle_list.append(v_out)
        
    return vehicle_list

@router.post("/vehicles", response_model=VehicleOut)
async def add_vehicle(vehicle: VehicleCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    new_vehicle = Vehicle(
        name=vehicle.name,
        vin=vehicle.vin,
        owner_id=current_user.id
    )
    db.add(new_vehicle)
    await db.commit()
    await db.refresh(new_vehicle)
    return new_vehicle

# --- Telemetry & Analytics ---
from fastapi import BackgroundTasks
from backend.services.analytics import analytics_engine

async def process_telemetry_ai(telemetry_id: int, db_session: AsyncSession, data_dict: dict):
    # Calculate AI scores in background
    scores = analytics_engine.calculate_risk_scores(data_dict)
    
    # Update record
    result = await db_session.execute(select(Telemetry).where(Telemetry.id == telemetry_id))
    telemetry = result.scalars().first()
    if telemetry:
        telemetry.collision_probability = scores["collision_probability"]
        telemetry.unsafe_score = scores["unsafe_score"]
        await db_session.commit()

@router.post("/telemetry", response_model=TelemetryOut)
async def ingest_telemetry(data: TelemetryCreate, db: AsyncSession = Depends(get_session)):
    # Calculate AI scores (synchronous for /telemetry legacy)
    scores = analytics_engine.calculate_risk_scores(data.model_dump())
    
    new_telemetry = Telemetry(
        **data.model_dump(),
        **scores
    )
    db.add(new_telemetry)
    await db.commit()
    await db.refresh(new_telemetry)
    return new_telemetry

@router.post("/telemetry/live")
async def ingest_live_telemetry(
    data: TelemetryLive, 
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_session)
):
    """
    Real-time hardware ingestion endpoint.
    Returns immediately to the OBU while processing AI in background.
    """
    # Create record with 0 scores initially
    new_telemetry = Telemetry(
        **data.model_dump(),
        collision_probability=0.0,
        unsafe_score=0.0
    )
    db.add(new_telemetry)
    await db.commit()
    await db.refresh(new_telemetry)
    
    # Queue AI processing
    background_tasks.add_task(process_telemetry_ai, new_telemetry.id, db, data.model_dump())
    
    # Quick risk estimate for immediate feedback (simplified)
    quick_status = "safe" if data.speed < 80 and abs(data.acceleration) < 4 else "warning"
    
    return {
        "telemetry_id": new_telemetry.id,
        "status": quick_status,
        "received_at": datetime.utcnow()
    }

@router.get("/dashboard/summary", response_model=VehicleStats)
async def get_dashboard_summary(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    # Get vehicles
    v_result = await db.execute(select(Vehicle).where(Vehicle.owner_id == current_user.id))
    vehicles = v_result.scalars().all()
    v_ids = [v.id for v in vehicles]
    
    if not v_ids:
        return VehicleStats(vehicle_count=0, total_telemetry=0, avg_unsafe_score=0, last_communication=None)
    
    # Get telemetry stats
    t_result = await db.execute(select(Telemetry).where(Telemetry.vehicle_id.in_(v_ids)))
    telemetries = t_result.scalars().all()
    
    total_t = len(telemetries)
    avg_unsafe = sum(t.unsafe_score for t in telemetries) / total_t if total_t > 0 else 0
    last_comm = max(t.timestamp for t in telemetries) if total_t > 0 else None
    
    return VehicleStats(
        vehicle_count=len(vehicles),
        total_telemetry=total_t,
        avg_unsafe_score=round(avg_unsafe, 2),
        last_communication=last_comm
    )
