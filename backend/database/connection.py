import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from backend.config import settings

logger = logging.getLogger(__name__)

engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionFactory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_db():
    """Initialize database with fallback."""
    global engine, AsyncSessionFactory
    try:
        # Try to connect/init (if meta was available, we'd use Base.metadata.create_all)
        # For backend, we'll just check if connection works
        async with engine.connect() as conn:
            await conn.execute("SELECT 1")
        logger.info("Backend database connected (PostgreSQL)")
    except Exception as exc:
        logger.warning("Backend PostgreSQL failed (%s), falling back to SQLite", exc)
        sqlite_url = "sqlite+aiosqlite:///./smartv2x_backend.db"
        engine = create_async_engine(sqlite_url)
        AsyncSessionFactory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        logger.info("Backend database switched to SQLite")

async def get_session() -> AsyncSession:
    async with AsyncSessionFactory() as session:
        yield session
