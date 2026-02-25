import os
import random
import threading
from datetime import datetime
from typing import List, Optional, Dict

from flask import Blueprint, request, jsonify, abort
from sqlalchemy import select

from backend.database.connection import SessionFactory
from backend.database.models import User, Vehicle, TelemetryRecord, RiskAnalysisResult
from backend.api.auth import (
    get_password_hash, 
    verify_password, 
    create_access_token, 
    get_current_user
)
from backend.services.ai_engine import AIRiskEngine
from backend.services.simulation import V2XSimulator
from backend.config import settings

routes_bp = Blueprint("routes", __name__)

# Global simulator instance
SIM_URL = os.getenv("V2X_INTERNAL_API", "http://localhost:3000")
simulator = V2XSimulator(api_url=SIM_URL)

# --- Auth Routes ---
@routes_bp.route("/auth/register", methods=["POST"])
def register():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    name = data.get("name")
    
    if not username or not password:
        abort(400, description="Username and password required")
        
    with SessionFactory() as db:
        existing = db.execute(select(User).where(User.username == username)).scalars().first()
        if existing:
            abort(400, description="Username taken")
        
        new_user = User(
            username=username,
            password_hash=get_password_hash(password),
            name=name
        )
        db.add(new_user)
        db.commit()
        
        access_token = create_access_token(data={"sub": new_user.username})
        return jsonify({"access_token": access_token, "token_type": "bearer"})

@routes_bp.route("/auth/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    
    with SessionFactory() as db:
        user = db.execute(select(User).where(User.username == username)).scalars().first()
        if not user or not verify_password(password, user.password_hash):
            abort(401, description="Invalid credentials")
        
        access_token = create_access_token(data={"sub": user.username})
        return jsonify({"access_token": access_token, "token_type": "bearer"})

# --- Telemetry & AI ---
@routes_bp.route("/telemetry", methods=["POST"])
def ingest_telemetry():
    data = request.get_json()
    vehicle_id = data.get("vehicle_id")
    latitude = data.get("latitude")
    longitude = data.get("longitude")
    speed = data.get("speed")
    acceleration = data.get("acceleration", 0.0)
    heading = data.get("heading")
    timestamp_str = data.get("timestamp")
    
    timestamp = datetime.fromisoformat(timestamp_str) if timestamp_str else datetime.utcnow()

    with SessionFactory() as db:
        record = TelemetryRecord(
            vehicle_id=vehicle_id,
            latitude=latitude,
            longitude=longitude,
            speed=speed,
            acceleration=acceleration,
            heading=heading,
            timestamp=timestamp
        )
        db.add(record)
        db.commit()
        db.refresh(record)

        # AI Analysis
        risk_score, risk_status = AIRiskEngine.estimate_collision_probability(
            {"lat": latitude, "lng": longitude, "speed": speed},
            [] # Populated in V2X production scenario
        )

        risk_analysis = RiskAnalysisResult(
            telemetry_id=record.id,
            risk_score=risk_score,
            status=risk_status,
            threat_description=f"Calculated risk levels for {vehicle_id}"
        )
        db.add(risk_analysis)
        db.commit()

        return jsonify({
            "id": record.id,
            "risk_score": risk_score,
            "status": risk_status,
            "timestamp": record.timestamp.isoformat()
        })

# --- Vehicle Management ---
@routes_bp.route("/vehicles", methods=["GET"])
def get_vehicles():
    current_user = get_current_user()
    with SessionFactory() as db:
        vehicles = db.execute(select(Vehicle).where(Vehicle.owner_id == current_user.id)).scalars().all()
        return jsonify([{
            "id": v.id,
            "name": v.name,
            "vin": v.vin,
            "created_at": v.created_at.isoformat(),
            "status": v.status
        } for v in vehicles])

@routes_bp.route("/vehicles", methods=["POST"])
def create_vehicle():
    current_user = get_current_user()
    data = request.get_json()
    new_v = Vehicle(name=data.get("name"), vin=data.get("vin"), owner_id=current_user.id)
    with SessionFactory() as db:
        db.add(new_v)
        db.commit()
        db.refresh(new_v)
        return jsonify({
            "id": new_v.id,
            "name": new_v.name,
            "vin": new_v.vin,
            "created_at": new_v.created_at.isoformat(),
            "status": new_v.status
        })

@routes_bp.route("/vehicles/locations", methods=["GET"])
def get_locations():
    current_user = get_current_user()
    with SessionFactory() as db:
        vehicles = db.execute(select(Vehicle).where(Vehicle.owner_id == current_user.id)).scalars().all()
        locations = []
        for v in vehicles:
            t = db.execute(
                select(TelemetryRecord)
                .where(TelemetryRecord.vehicle_id == v.id)
                .order_by(TelemetryRecord.timestamp.desc())
                .limit(1)
            ).scalars().first()
            
            if t:
                r = db.execute(select(RiskAnalysisResult).where(RiskAnalysisResult.telemetry_id == t.id)).scalars().first()
                locations.append({
                    "id": v.id,
                    "name": v.name,
                    "latitude": t.latitude,
                    "longitude": t.longitude,
                    "speed": t.speed,
                    "risk_status": r.status if r else "SAFE",
                    "risk_score": r.risk_score if r else 0.0
                })
        return jsonify(locations)

@routes_bp.route("/dashboard/summary", methods=["GET"])
def get_dashboard_summary():
    current_user = get_current_user()
    with SessionFactory() as db:
        vehicles = db.execute(select(Vehicle).where(Vehicle.owner_id == current_user.id)).scalars().all()
        v_ids = [v.id for v in vehicles]
        
        telemetry_count = db.execute(select(TelemetryRecord).where(TelemetryRecord.vehicle_id.in_(v_ids))).scalars().all()
        
        results = db.execute(
            select(RiskAnalysisResult)
            .join(TelemetryRecord)
            .where(TelemetryRecord.vehicle_id.in_(v_ids))
            .order_by(RiskAnalysisResult.id.desc())
            .limit(100)
        ).scalars().all()
        
        avg_score = sum(r.risk_score for r in results) / len(results) if results else 0.0
        
        last_comm = db.execute(
            select(TelemetryRecord)
            .where(TelemetryRecord.vehicle_id.in_(v_ids))
            .order_by(TelemetryRecord.timestamp.desc())
            .limit(1)
        ).scalars().first()
        
        return jsonify({
            "vehicle_count": len(vehicles),
            "total_telemetry": len(telemetry_count),
            "avg_unsafe_score": round(avg_score * 100, 2),
            "last_communication": last_comm.timestamp.isoformat() if last_comm else None,
            "insights": [
                "Fleet density is optimal",
                "No high-speed violations detected",
                "Simulation nodes performing as expected"
            ]
        })

# --- Simulation Controls ---
@routes_bp.route("/simulation/start", methods=["POST"])
def start_sim():
    current_user = get_current_user()
    if simulator.is_running:
        return jsonify({"status": "already running"})
    
    with SessionFactory() as db:
        vehicles = db.execute(select(Vehicle).where(Vehicle.owner_id == current_user.id)).scalars().all()
        if not vehicles:
            abort(400, description="No vehicles found. Register at least one.")
            
        sim_vehicles = [{
            "id": v.id,
            "name": v.name,
            "lat": 37.7749 + (random.random() - 0.5) * 0.05,
            "lng": -122.4194 + (random.random() - 0.5) * 0.05,
            "speed": 40.0 + random.random() * 20,
            "heading": random.randint(0, 359),
            "acceleration": 0.0
        } for v in vehicles]
        
        # Start in background thread
        thread = threading.Thread(target=simulator.start, args=(sim_vehicles,))
        thread.daemon = True
        thread.start()
        
        return jsonify({"status": f"V2X Swarm launched for {len(sim_vehicles)} vehicles."})

@routes_bp.route("/simulation/stop", methods=["POST"])
def stop_sim():
    simulator.stop()
    return jsonify({"status": "simulation terminated"})
