"""
SmartV2X-CP Ultra — Edge RSU Server Entry Point
=================================================
FastAPI application with CORS, rate limiting, JWT auth,
WebSocket live feed, and service modules.

Run:
  uvicorn edge_rsu.main:app --host 0.0.0.0 --port 8000 --reload
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from edge_rsu.config import settings
from edge_rsu.api import vehicle_router, health_router, ws_router, routes_auth
from edge_rsu.middleware.rate_limiter import RateLimiterMiddleware
from edge_rsu.cache.redis_client import RedisCache
from edge_rsu.database.connection import init_db

# ── Logging ───────────────────────────────────────────────
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(settings.LOG_FILE, mode="a"),
    ],
)
logger = logging.getLogger("edge_rsu")

# ── Redis instance ────────────────────────────────────────
redis_cache = RedisCache(settings.REDIS_URL)


# ── Lifespan ──────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    logger.info("══════════════════════════════════════════")
    logger.info("  SmartV2X-CP Ultra — Edge RSU Server")
    logger.info("══════════════════════════════════════════")
    await redis_cache.connect()
    await init_db()
    logger.info("Edge RSU server ready on %s:%d", settings.HOST, settings.PORT)
    yield
    await redis_cache.close()
    logger.info("Edge RSU server shutting down")


# ── FastAPI app ───────────────────────────────────────────
app = FastAPI(
    title="SmartV2X-CP Ultra — Edge RSU",
    description="Real-time V2X collision prediction edge server",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting
app.add_middleware(
    RateLimiterMiddleware,
    max_requests=settings.RATE_LIMIT_PER_SECOND,
)

# ── Mount routers ─────────────────────────────────────────
app.include_router(vehicle_router)
app.include_router(health_router)
app.include_router(ws_router)
app.include_router(routes_auth.router)


# ── Root ──────────────────────────────────────────────────
@app.get("/")
async def root():
    return {
        "service": "SmartV2X-CP Ultra Edge RSU",
        "version": "1.0.0",
        "docs": "/docs",
    }
