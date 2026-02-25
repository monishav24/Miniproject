from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime
import asyncio
import os
import random

from backend.database.connection import get_session
from backend.database.models import User, Vehicle, TelemetryRecord, RiskAnalysisResult, SimulationRun
from backend.api.auth import (
    get_password_hash, 
    verify_password, 
    create_access_token, 
    get_current_user
)
from backend.services.ai_engine import AIRiskEngine
from backend.services.simulation import V2XSimulator
from backend.config import settings

router = APIRouter()

# Global simulator instance for demo
SIM_URL = os.getenv("V2X_INTERNAL_API", "http://localhost:3000")
simulator = V2XSimulator(api_url=SIM_URL)

# --- Schemas ---
class UserRegister(BaseModel):
    username: str
    password: str
    name: Optional[str] = None

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
    acceleration: float = 0.0
    heading: Optional[float] = None
    timestamp: Optional[datetime] = None

class RiskResultOut(BaseModel):
    risk_score: float
    status: str
    threat_description: Optional[str] = None

class TelemetryOut(BaseModel):
    id: int
    vehicle_id: int
    timestamp: datetime
    latitude: float
    longitude: float
    speed: float
    risk_results: List[RiskResultOut] = []
    class Config:
        from_attributes = True

class VehicleOut(VehicleBase):
    id: int
    created_at: datetime
    status: str
    class Config:
        from_attributes = True

class VehicleLocation(BaseModel):
    id: int
    name: str
    latitude: float
    longitude: float
    speed: float
    risk_status: str
    risk_score: float

# --- Auth Routes ---
@router.post("/auth/register", response_model=Token)
async def register(user_data: UserRegister, db: AsyncSession = Depends(get_session)):
    result = await db.execute(select(User).where(User.username == user_data.username))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Username taken")
    
    new_user = User(
        username=user_data.username,
        password_hash=get_password_hash(user_data.password),
        name=user_data.name
    )
    db.add(new_user)
    await db.commit()
    
    access_token = create_access_token(data={"sub": new_user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/auth/login", response_model=Token)
async def login(user_data: UserLogin, db: AsyncSession = Depends(get_session)):
    result = await db.execute(select(User).where(User.username == user_data.username))
    user = result.scalars().first()
    if not user or not verify_password(user_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

# --- Telemetry & AI ---
@router.post("/telemetry")
async def ingest_telemetry(data: TelemetryCreate, db: AsyncSession = Depends(get_session)):
    """
    Industry-grade telemetry ingestion with real-time AI risk analysis.
    """
    # 1. Store Telemetry
    record = TelemetryRecord(
        vehicle_id=data.vehicle_id,
        latitude=data.latitude,
        longitude=data.longitude,
        speed=data.speed,
        acceleration=data.acceleration,
        heading=data.heading,
        timestamp=data.timestamp or datetime.utcnow()
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    # 2. Run AI Analysis (Simulated context for demo)
    # In production, we'd fetch nearby vehicles from a spatial index/cache
    risk_score, risk_status = AIRiskEngine.estimate_collision_probability(
        {"lat": data.latitude, "lng": data.longitude, "speed": data.speed},
        [] # Empty for individual report, would be populated in real V2X scenario
    )

    # 3. Save Analysis
    risk_analysis = RiskAnalysisResult(
        telemetry_id=record.id,
        risk_score=risk_score,
        status=risk_status,
        threat_description=f"Calculated risk levels for {data.vehicle_id}"
    )
    db.add(risk_analysis)
    await db.commit()

    return {
        "id": record.id,
        "risk_score": risk_score,
        "status": risk_status,
        "timestamp": record.timestamp
    }

# --- Vehicle Management ---
@router.get("/vehicles", response_model=List[VehicleOut])
async def get_vehicles(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    result = await db.execute(select(Vehicle).where(Vehicle.owner_id == current_user.id))
    return result.scalars().all()

@router.post("/vehicles", response_model=VehicleOut)
async def create_vehicle(vehicle: VehicleCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    new_v = Vehicle(name=vehicle.name, vin=vehicle.vin, owner_id=current_user.id)
    db.add(new_v)
    await db.commit()
    await db.refresh(new_v)
    return new_v

@router.get("/vehicles/locations", response_model=List[VehicleLocation])
async def get_locations(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    # Optimized fetch for map
    result = await db.execute(select(Vehicle).where(Vehicle.owner_id == current_user.id))
    vehicles = result.scalars().all()
    
    locations = []
    for v in vehicles:
        # Get latest telemetry + risk
        t_q = await db.execute(
            select(TelemetryRecord)
            .where(TelemetryRecord.vehicle_id == v.id)
            .order_by(TelemetryRecord.timestamp.desc())
            .limit(1)
        )
        t = t_q.scalars().first()
        if t:
            r_q = await db.execute(select(RiskAnalysisResult).where(RiskAnalysisResult.telemetry_id == t.id).limit(1))
            r = r_q.scalars().first()
            locations.append(VehicleLocation(
                id=v.id,
                name=v.name,
                latitude=t.latitude,
                longitude=t.longitude,
                speed=t.speed,
                risk_status=r.status if r else "SAFE",
                risk_score=r.risk_score if r else 0.0
            ))
    return locations

@router.get("/dashboard/summary")
async def get_dashboard_summary(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    """
    Returns aggregate stats for the AI Insights panel.
    """
    # 1. Vehicle Count
    v_q = await db.execute(select(Vehicle).where(Vehicle.owner_id == current_user.id))
    vehicles = v_q.scalars().all()
    v_ids = [v.id for v in vehicles]
    
    # 2. Total Telemetry
    t_q = await db.execute(select(TelemetryRecord).where(TelemetryRecord.vehicle_id.in_(v_ids)))
    telemetry_count = len(t_q.scalars().all())
    
    # 3. Avg Safety/Unsafe Score
    # For demo, we'll calculate this from recent risk results
    r_q = await db.execute(
        select(RiskAnalysisResult)
        .join(TelemetryRecord)
        .where(TelemetryRecord.vehicle_id.in_(v_ids))
        .order_by(RiskAnalysisResult.id.desc())
        .limit(100)
    )
    results = r_q.scalars().all()
    avg_score = sum(r.risk_score for r in results) / len(results) if results else 0.0
    
    # 4. Last Communication
    last_t = await db.execute(
        select(TelemetryRecord)
        .where(TelemetryRecord.vehicle_id.in_(v_ids))
        .order_by(TelemetryRecord.timestamp.desc())
        .limit(1)
    )
    last_comm = last_t.scalars().first()
    
    return {
        "vehicle_count": len(vehicles),
        "total_telemetry": telemetry_count,
        "avg_unsafe_score": round(avg_score * 100, 2),
        "last_communication": last_comm.timestamp if last_comm else None,
        "insights": [
            "Fleet density is optimal",
            "No high-speed violations detected",
            "Simulation nodes performing as expected"
        ]
    }

# --- Simulation Controls ---
@router.post("/simulation/start")
async def start_sim(background_tasks: BackgroundTasks, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    """Starts simulation only for the current user's registered vehicles."""
    if simulator.is_running:
        return {"status": "already running"}
    
    # 1. Fetch current user's vehicles
    v_q = await db.execute(select(Vehicle).where(Vehicle.owner_id == current_user.id))
    vehicles = v_q.scalars().all()
    
    if not vehicles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="No vehicles found. Please register at least one vehicle before launching the swarm."
        )
    
    # 2. Build vehicle list for simulator with initial random positions
    sim_vehicles = []
    for v in vehicles:
        sim_vehicles.append({
            "id": v.id,
            "name": v.name,
            "lat": 37.7749 + (random.random() - 0.5) * 0.05,
            "lng": -122.4194 + (random.random() - 0.5) * 0.05,
            "speed": 40.0 + random.random() * 20,
            "heading": random.randint(0, 359),
            "acceleration": 0.0
        })
    
    # 3. Launch background task
    background_tasks.add_task(simulator.start, sim_vehicles)
    return {"status": f"V2X Swarm launched for {len(sim_vehicles)} registered vehicles."}

@router.post("/simulation/stop")
async def stop_sim():
    simulator.stop()
    return {"status": "simulation terminated"}
