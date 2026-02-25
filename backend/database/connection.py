import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from backend.config import settings
from backend.database.models import Base

logger = logging.getLogger(__name__)

# Ensure DATABASE_URL is set for psycopg2 if it's postgres
db_url = settings.DATABASE_URL
# psycogp2 uses postgresql://, unlike asyncpg which needs +asyncpg
# However, many Render URLs might already have it or not. 
# We'll just ensure it's a standard postgresql:// URL.
if db_url.startswith("postgresql+asyncpg://"):
    db_url = db_url.replace("postgresql+asyncpg://", "postgresql://", 1)

# Production-grade engine configuration
# SSL is required for Render Postgres
connect_args = {"sslmode": "require"} if "postgresql" in db_url else {}

engine = create_engine(
    db_url, 
    echo=False,
    pool_pre_ping=True,
    connect_args=connect_args
)
SessionFactory = sessionmaker(bind=engine, expire_on_commit=False)

def init_db():
    """Initialize database and create tables."""
    try:
        logger.info("Initializing backend database tables...")
        Base.metadata.create_all(engine)
        logger.info("Backend database initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")

def get_session():
    session = SessionFactory()
    try:
        yield session
    finally:
        session.close()
