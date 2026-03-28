"""
Temporal Network Analysis Platform — FastAPI Backend
"""
import asyncio
import json
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.collector.traffic_generator import TrafficCollector, NODE_META
from backend.database.db import (
    init_db, save_snapshot, get_snapshot, list_snapshots,
    get_timeline, tag_snapshot, list_experiments
)
from backend.replay_engine.replay import replay_engine
from backend.simulation_engine.simulator import simulate_alternatives, get_architecture_recommendation
from backend.prediction_engine.predictor import get_predictor
from backend.analysis_engine.rca import analyze_root_causes
from backend.analysis_engine.fingerprint import (
    generate_fingerprint, fingerprint_similarity,
    fingerprint_evolution, detect_anomaly
)
from backend.analysis_engine.recommender import generate_recommendations
from backend.experiment_runner.runner import run_experiment_suite

# ─── Globals ─────────────────────────────────────────────────────────────────
collector    = TrafficCollector(interval=1.0)
predictor    = get_predictor(list(NODE_META.keys()))
_fingerprint_history: List[str] = []
_connected_ws: List[WebSocket] = []
_latest_snapshot: Optional[dict] = None
_rca_cache: List[dict] = []
_alerts: List[dict]    = []


async def _broadcast(data: dict):
    dead = []
    for ws in _connected_ws:
        try:
            await ws.send_text(json.dumps(data))
        except Exception:
            dead.append(ws)
    for ws in dead:
        _connected_ws.remove(ws)


def _on_snapshot(snap: dict):
    global _latest_snapshot, _rca_cache

    # Persist every 5th tick to avoid DB bloat
    if snap["tick"] % 5 == 0:
        save_snapshot(snap, tag="auto")

    # Prediction ingestion
    predictor.ingest_snapshot(snap)

    # RCA (every 3 ticks)
    if snap["tick"] % 3 == 0:
        _rca_cache = analyze_root_causes(snap)

    # Fingerprint history
    _fingerprint_history.append(snap["fingerprint"])
    if len(_fingerprint_history) > 200:
        _fingerprint_history.pop(0)

    # Alerts
    global _alerts
    new_alerts = []
    for cause in _rca_cache:
        if cause.get("confidence", 0) > 0.7:
            new_alerts.append({
                "tick":        snap["tick"],
                "timestamp":   time.time(),
                "type":        cause["cause"],
                "severity":    cause.get("severity", "medium"),
                "confidence":  cause["confidence"],
                "description": cause["description"],
            })
    if new_alerts:
        _alerts = (new_alerts + _alerts)[:50]

    _latest_snapshot = snap

    # Broadcast via WebSocket (schedule coroutine thread-safely)
    payload = {
        "type":    "snapshot",
        "data":    snap,
        "rca":     _rca_cache[:3],
        "alerts":  _alerts[:5],
    }
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.run_coroutine_threadsafe(_broadcast(payload), loop)
    except RuntimeError:
        pass


# ─── App lifecycle ────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    collector.add_callback(_on_snapshot)
    collector.start()
    yield
    collector.stop()


app = FastAPI(
    title="Temporal Network Analysis Platform",
    description="Research prototype for telecom temporal network analysis",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── WebSocket ────────────────────────────────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    _connected_ws.append(ws)
    try:
        # Send initial state
        if _latest_snapshot:
            await ws.send_text(json.dumps({
                "type": "snapshot",
                "data": _latest_snapshot,
                "rca":  _rca_cache[:3],
                "alerts": _alerts[:5],
            }))
        while True:
            await asyncio.sleep(0.5)
            msg = await asyncio.wait_for(ws.receive_text(), timeout=0.1)
            # Handle client control messages
            try:
                cmd = json.loads(msg)
                if cmd.get("action") == "surge":
                    collector.trigger_surge(duration=cmd.get("duration", 15))
                    await ws.send_text(json.dumps({"type": "ack", "action": "surge"}))
            except Exception:
                pass
    except (WebSocketDisconnect, asyncio.TimeoutError):
        pass
    except Exception:
        pass
    finally:
        if ws in _connected_ws:
            _connected_ws.remove(ws)


# ─── Snapshot APIs ────────────────────────────────────────────────────────────
@app.get("/api/snapshot/latest")
def get_latest():
    if _latest_snapshot is None:
        raise HTTPException(404, "No snapshot yet")
    return _latest_snapshot


@app.get("/api/snapshot/{snap_id}")
def get_snap(snap_id: int):
    s = get_snapshot(snap_id)
    if not s:
        raise HTTPException(404, "Snapshot not found")
    return s


@app.get("/api/snapshots")
def list_snaps(limit: int = 100, offset: int = 0):
    return list_snapshots(limit=limit, offset=offset)


@app.get("/api/timeline")
def timeline(limit: int = 200):
    return get_timeline(limit=limit)


class TagRequest(BaseModel):
    label: str
    tag: str = "manual"


@app.post("/api/snapshot/{snap_id}/tag")
def tag_snap(snap_id: int, req: TagRequest):
    tag_snapshot(snap_id, req.label, req.tag)
    return {"ok": True}


# ─── Replay APIs ──────────────────────────────────────────────────────────────
@app.get("/api/replay/go/{snap_id}")
def replay_go(snap_id: int):
    s = replay_engine.go_to_snapshot(snap_id)
    if not s:
        raise HTTPException(404, "Snapshot not found")
    return s


@app.get("/api/replay/rewind")
def replay_rewind(steps: int = 1):
    s = replay_engine.rewind(steps=steps)
    return s or {}


@app.get("/api/replay/forward")
def replay_forward(steps: int = 1):
    s = replay_engine.fast_forward(steps=steps)
    return s or {}


@app.get("/api/replay/start")
def replay_start():
    return replay_engine.go_to_start() or {}


@app.get("/api/replay/end")
def replay_end():
    return replay_engine.go_to_end() or {}


@app.get("/api/replay/compare/{id_a}/{id_b}")
def replay_compare(id_a: int, id_b: int):
    return replay_engine.compare(id_a, id_b)


@app.get("/api/replay/status")
def replay_status():
    return {
        "cursor":  replay_engine.cursor_position,
        "total":   replay_engine.get_total(),
    }


# ─── Simulation APIs ──────────────────────────────────────────────────────────
@app.get("/api/simulate/alternatives")
def simulate():
    if _latest_snapshot is None:
        raise HTTPException(503, "Waiting for first snapshot")
    alts = simulate_alternatives(_latest_snapshot)
    rec  = get_architecture_recommendation(alts)
    return {"alternatives": alts, "recommendation": rec}


# ─── Prediction APIs ──────────────────────────────────────────────────────────
@app.get("/api/predict")
def predict():
    result = predictor.predict()
    hotspots = predictor.get_hotspots(threshold=0.6)
    return {**result, "hotspots": hotspots}


# ─── Analysis APIs ────────────────────────────────────────────────────────────
@app.get("/api/rca")
def rca():
    if _latest_snapshot is None:
        raise HTTPException(503, "Waiting for first snapshot")
    causes = analyze_root_causes(_latest_snapshot)
    return {"causes": causes, "tick": _latest_snapshot["tick"]}


@app.get("/api/rca/snapshot/{snap_id}")
def rca_snapshot(snap_id: int):
    s = get_snapshot(snap_id)
    if not s:
        raise HTTPException(404, "Snapshot not found")
    topo = s["topology"]
    snap_view = {
        "nodes": topo.get("nodes", []),
        "edges": topo.get("edges", []),
        "metrics": s["metrics"],
        "tick": s["tick"],
    }
    return {"causes": analyze_root_causes(snap_view)}


@app.get("/api/fingerprint")
def fingerprint_status():
    fp = _latest_snapshot["fingerprint"] if _latest_snapshot else "none"
    anomaly = detect_anomaly(fp, _fingerprint_history[:-1])
    evolution = fingerprint_evolution(_fingerprint_history)
    return {
        "current":   fp,
        "anomaly":   anomaly,
        "evolution": evolution,
    }


@app.get("/api/recommend")
def recommend():
    if _latest_snapshot is None:
        raise HTTPException(503, "Waiting for first snapshot")
    alts   = simulate_alternatives(_latest_snapshot)
    causes = analyze_root_causes(_latest_snapshot)
    recs   = generate_recommendations(_latest_snapshot, causes, alts)
    return {"recommendations": recs}


# ─── Experiment APIs ──────────────────────────────────────────────────────────
@app.post("/api/experiment/run")
async def run_experiment(background_tasks: BackgroundTasks):
    if _latest_snapshot is None:
        raise HTTPException(503, "Waiting for first snapshot")
    snap = dict(_latest_snapshot)
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, run_experiment_suite, snap)
    return result


@app.get("/api/experiments")
def get_experiments(limit: int = 20):
    return list_experiments(limit=limit)


# ─── Control APIs ─────────────────────────────────────────────────────────────
@app.post("/api/control/surge")
def trigger_surge(duration: int = 15):
    collector.trigger_surge(duration=duration)
    return {"ok": True, "duration": duration}


@app.get("/api/alerts")
def get_alerts():
    return {"alerts": _alerts[:20]}


@app.get("/api/health")
def health():
    return {
        "status":     "ok",
        "tick":       _latest_snapshot["tick"] if _latest_snapshot else 0,
        "live":       collector.live_capture,
        "ws_clients": len(_connected_ws),
    }
