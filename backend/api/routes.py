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
    return result.scalars().all()

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
from backend.services.analytics import analytics_engine

@router.post("/telemetry", response_model=TelemetryOut)
async def ingest_telemetry(data: TelemetryCreate, db: AsyncSession = Depends(get_session)):
    # Calculate AI scores
    scores = analytics_engine.calculate_risk_scores(data.model_dump())
    
    new_telemetry = Telemetry(
        **data.model_dump(),
        **scores
    )
    db.add(new_telemetry)
    await db.commit()
    await db.refresh(new_telemetry)
    return new_telemetry

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
