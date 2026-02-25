"""
SmartV2X-CP Ultra — Vehicle API Routes
========================================
POST /api/vehicle/register — register a new OBU
POST /api/vehicle/update  — receive real-time vehicle update
POST /api/vehicle/heartbeat — heartbeat keep-alive
GET  /api/vehicle/list     — list all active vehicles
"""

import time
import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime

from edge_rsu.database.connection import get_db
from edge_rsu.database.models import Vehicle
from edge_rsu.auth.jwt_handler import get_current_user
from edge_rsu.auth.rbac import RoleChecker

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/vehicle", tags=["Vehicle"])

# ── In-memory vehicle store (cache for real-time state) ──
_vehicles: Dict[str, Dict[str, Any]] = {}


# ── Pydantic schemas ──────────────────────────────────────
class VehicleRegisterRequest(BaseModel):
    vehicle_id: str
    device_name: str = ""
    firmware_version: str = ""

class VehicleUpdateRequest(BaseModel):
    vehicle_id: str
    timestamp: float
    position: Dict[str, float] = Field(default_factory=dict)
    state: Dict[str, float] = Field(default_factory=dict)
    risk: Dict[str, Any] = Field(default_factory=dict)
    trajectory: list = Field(default_factory=list)

class HeartbeatRequest(BaseModel):
    vehicle_id: str
    timestamp: float

class VehicleResponse(BaseModel):
    status: str
    message: str
    data: Optional[Dict] = None


# ── Routes ────────────────────────────────────────────────
@router.post("/register", response_model=VehicleResponse)
async def register_vehicle(
    req: VehicleRegisterRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Register a new OBU device with the edge server."""
    # Check if already in DB
    result = await db.execute(select(Vehicle).where(Vehicle.vehicle_id == req.vehicle_id))
    db_vehicle = result.scalars().first()
    
    if not db_vehicle:
        db_vehicle = Vehicle(
            vehicle_id=req.vehicle_id,
            device_name=req.device_name,
            firmware_version=req.firmware_version,
            status="online"
        )
        db.add(db_vehicle)
        await db.commit()
        await db.refresh(db_vehicle)

    # Sync to in-memory store
    _vehicles[req.vehicle_id] = {
        "vehicle_id": req.vehicle_id,
        "device_name": req.device_name,
        "firmware_version": req.firmware_version,
        "registered_at": time.time(),
        "last_seen": time.time(),
        "status": "online",
        "position": {},
        "state": {},
        "risk": {"level": "LOW"},
    }
    logger.info("Vehicle registered: %s by %s", req.vehicle_id, user["username"])
    return VehicleResponse(
        status="ok",
        message=f"Vehicle {req.vehicle_id} registered",
        data={"vehicle_id": req.vehicle_id},
    )


@router.post("/update", response_model=VehicleResponse)
async def update_vehicle(
    req: VehicleUpdateRequest,
    user: dict = Depends(get_current_user),
):
    """Receive real-time vehicle state update."""
    if req.vehicle_id not in _vehicles:
        # Auto-register in-memory if unknown (production would check DB)
        _vehicles[req.vehicle_id] = {
            "vehicle_id": req.vehicle_id,
            "registered_at": time.time(),
            "status": "online",
        }

    _vehicles[req.vehicle_id].update({
        "last_seen": time.time(),
        "position": req.position,
        "state": req.state,
        "risk": req.risk,
        "trajectory": req.trajectory,
        "status": "online",
    })

    # Broadcast via WebSocket (imported lazily to avoid circular imports)
    from edge_rsu.api.websocket import broadcast_vehicle_update
    await broadcast_vehicle_update(req.vehicle_id, _vehicles[req.vehicle_id])

    return VehicleResponse(status="ok", message="Update received")


@router.post("/heartbeat", response_model=VehicleResponse)
async def heartbeat(
    req: HeartbeatRequest,
    user: dict = Depends(get_current_user),
):
    """Heartbeat keep-alive from OBU device."""
    if req.vehicle_id in _vehicles:
        _vehicles[req.vehicle_id]["last_seen"] = time.time()
        _vehicles[req.vehicle_id]["status"] = "online"
    return VehicleResponse(status="ok", message="Heartbeat acknowledged")


@router.get("/list")
async def list_vehicles(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all registered vehicles and their latest state."""
    # 1. Fetch from DB to ensure all registered vehicles are present
    result = await db.execute(select(Vehicle))
    db_vehicles = result.scalars().all()
    
    # 2. Merge with in-memory real-time state
    now = time.time()
    response_list = []
    
    for v in db_vehicles:
        # Get live data if available
        live = _vehicles.get(v.vehicle_id, {})
        
        # Check if offline
        status = live.get("status", "offline")
        last_seen = live.get("last_seen", 0)
        if last_seen > 0 and now - last_seen > 30:
            status = "offline"
            
        response_list.append({
            "vehicle_id": v.vehicle_id,
            "device_name": v.device_name,
            "status": status,
            "position": live.get("position", {"lat": v.latitude, "lng": v.longitude}),
            "risk": live.get("risk", {"level": "LOW"}),
            "last_seen": last_seen
        })
        
    return {"vehicles": response_list, "count": len(response_list)}


def get_vehicles_store() -> Dict[str, Dict[str, Any]]:
    """Expose the vehicle store to other modules."""
    return _vehicles


def get_vehicles_store() -> Dict[str, Dict[str, Any]]:
    """Expose the vehicle store to other modules."""
    return _vehicles
