"""
SmartV2X-CP Ultra — Health & Analytics Routes
===============================================
GET /api/health           — system health check
GET /api/analytics        — basic analytics summary
GET /api/collision-history — recent collision events
"""

import time
import logging

from fastapi import APIRouter

logger = logging.getLogger(__name__)
router = APIRouter(tags=["System"])

# ── In-memory collision log ───────────────────────────────
_collision_events: list = []


# ── Health ────────────────────────────────────────────────
@router.get("/api/health")
async def health_check():
    """System health endpoint."""
    from edge_rsu.api.routes_vehicle import get_vehicles_store
    vehicles = get_vehicles_store()
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "uptime_seconds": time.time() - _START_TIME,
        "active_vehicles": len([v for v in vehicles.values() if v.get("status") == "online"]),
        "total_vehicles": len(vehicles),
        "collision_events_total": len(_collision_events),
    }


# ── Analytics ─────────────────────────────────────────────
@router.get("/api/analytics")
async def analytics():
    """Basic analytics summary."""
    from edge_rsu.api.routes_vehicle import get_vehicles_store
    vehicles = get_vehicles_store()
    risk_counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
    for v in vehicles.values():
        level = v.get("risk", {}).get("level", "LOW")
        risk_counts[level] = risk_counts.get(level, 0) + 1
    return {
        "total_vehicles": len(vehicles),
        "risk_distribution": risk_counts,
        "total_collision_events": len(_collision_events),
        "timestamp": time.time(),
    }


# ── Collision history ─────────────────────────────────────
@router.get("/api/collision-history")
async def collision_history(limit: int = 50):
    """Return recent collision events."""
    return {
        "events": _collision_events[-limit:],
        "total": len(_collision_events),
    }


def log_collision_event(event: dict):
    """Append a collision event (called by risk aggregator)."""
    event["logged_at"] = time.time()
    _collision_events.append(event)
    if len(_collision_events) > 10000:
        _collision_events.pop(0)


_START_TIME = time.time()
