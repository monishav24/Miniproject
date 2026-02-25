"""
SmartV2X-CP Ultra — Database Connection Manager
==================================================
Async SQLAlchemy engine and session factory for PostgreSQL.
Falls back to SQLite for development/testing.
"""

import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from edge_rsu.config import settings

logger = logging.getLogger(__name__)

# Use SQLite fallback for development if PostgreSQL is not configured
_db_url = settings.DATABASE_URL
if "postgresql" in _db_url:
    try:
        import asyncpg  # noqa: F401
    except ImportError:
        logger.warning("asyncpg not installed — falling back to SQLite")
        _db_url = "sqlite+aiosqlite:///./smartv2x_edge.db"

engine = create_async_engine(_db_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    """Create all tables with fallback handling."""
    global engine, async_session
    from edge_rsu.database.models import Base
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables initialized (PostgreSQL)")
    except Exception as exc:
        logger.warning("PostgreSQL connection failed (%s), falling back to SQLite", exc)
        # Re-initialize engine with SQLite
        sqlite_url = "sqlite+aiosqlite:///./smartv2x_edge.db"
        engine = create_async_engine(sqlite_url)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables initialized (SQLite)")


async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session
