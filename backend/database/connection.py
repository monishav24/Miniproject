import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from backend.config import settings
from backend.database.models import Base

logger = logging.getLogger(__name__)

# Ensure DATABASE_URL is set for asyncpg if it's postgres
db_url = settings.DATABASE_URL
if db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

# Production-grade engine configuration
# SSL is required for Render Postgres
connect_args = {"ssl": "require"} if "postgresql" in db_url else {}

engine = create_async_engine(
    db_url, 
    echo=False,
    pool_pre_ping=True,
    connect_args=connect_args
)
AsyncSessionFactory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_db():
    """Initialize database and create tables."""
    try:
        async with engine.begin() as conn:
            logger.info("Initializing backend database tables...")
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Backend database initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        # Fallback to sqlite if needed for local dev, but for production we want this to error
        if "postgresql" not in db_url:
             async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

async def get_session() -> AsyncSession:
    async with AsyncSessionFactory() as session:
        try:
            yield session
        finally:
            await session.close()
