import logging
import os
import asyncio
from contextlib import asynccontextmanager

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Import Edge RSU components
from edge_rsu.config import settings as edge_settings
from edge_rsu.api import vehicle_router, health_router as edge_health, ws_router #, routes_auth
from edge_rsu.cache.redis_client import RedisCache
from edge_rsu.database.connection import init_db as init_edge_db

# Import Backend components
from backend.config import settings as backend_settings
from backend.api.routes import router as backend_api_router
from backend.api.health import router as backend_health_router
from backend.database.connection import init_db as init_backend_db

# ── Setup ───────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("unified_server")

# Use Edge redis settings for both if feasible, or init separate?
# For simplicity, we assume one Redis and one Postgres pair or consistent env vars.
# We will init both DBs.

redis_cache = RedisCache(edge_settings.REDIS_URL)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("⚡ STARTING UNIFIED SMARTV2X SERVER ⚡")
    
    # Init Databases
    await init_edge_db()
    await init_backend_db()
    
    # Connect Redis
    await redis_cache.connect()
    
    yield
    
    await redis_cache.close()
    logger.info("Unified server shutting down")

app = FastAPI(
    title="SmartV2X-CP Ultra — Unified Server",
    description="All-in-One: Edge, Backend, and Dashboard",
    lifespan=lifespan
)

# CORS - Allow all for sharable demo
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Mount APIs ──────────────────────────────────────────────
# Edge Routes (Vehicle, WebSocket) - Served at root / to match dashboard expectations if VITE_API_URL is empty
app.include_router(vehicle_router)  # /vehicle/...
app.include_router(edge_health)     # /api/health
app.include_router(ws_router)       # /ws/live
# Real Auth Implementation
from edge_rsu.api import routes_auth
app.include_router(routes_auth.router, tags=["Auth"])

# AI Analytics
from edge_rsu.api.routes_analytics import router as analytics_router
app.include_router(analytics_router, tags=["AI Analytics"])

# Backend Routes - Mount at /backend or /api/analytics?
# The original backend was separate. Let's prefix it.
app.include_router(backend_api_router, prefix="/backend/api")
app.include_router(backend_health_router, prefix="/backend")

# ── Serve Frontend ──────────────────────────────────────────
# Check if dist exists
dist_path = os.path.join(os.path.dirname(__file__), "dashboard", "dist")
if not os.path.exists(dist_path):
    # Fallback for dev environment positions
    dist_path = os.path.join(os.path.dirname(__file__), "..", "dashboard", "dist")

if os.path.exists(dist_path):
    logger.info(f"Serving dashboard from: {dist_path}")
    
    # Mount static assets first
    app.mount("/assets", StaticFiles(directory=os.path.join(dist_path, "assets")), name="assets")
    
    # Catch-all for SPA (return index.html)
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # Allow API routes to pass through (handled above if matched first? No, FastAPI matches in order)
        # Note: In FastAPI, specific routes must be defined BEFORE a catch-all.
        # Since we included routers first, they should take precedence.
        
        # Check if file exists in dist (e.g. favicon.ico)
        file_path = os.path.join(dist_path, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
            
        # Return index.html for everything else
        return FileResponse(os.path.join(dist_path, "index.html"))
else:
    logger.warning("Dashboard build not found! Run 'npm run build' in dashboard directory.")

if __name__ == "__main__":
    import uvicorn
    # Use PORT from environment (required for Render)
    port = int(os.environ.get("PORT", 3000))
    # Listen on 0.0.0.0 for sharing
    uvicorn.run(app, host="0.0.0.0", port=port)
