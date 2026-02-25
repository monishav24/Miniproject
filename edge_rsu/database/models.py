"""
SmartV2X-CP Ultra — Database ORM Models
=========================================
SQLAlchemy declarative models for the Edge RSU database.
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean, Text, JSON, Enum,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Vehicle(Base):
    """Registered vehicle / OBU device."""
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    vehicle_id = Column(String(64), unique=True, nullable=False, index=True)
    device_name = Column(String(128), default="")
    firmware_version = Column(String(32), default="")
    registered_at = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)
    status = Column(String(16), default="offline")       # online / offline
    latitude = Column(Float, default=0.0)
    longitude = Column(Float, default=0.0)
    metadata_json = Column(JSON, default=dict)


class CollisionEvent(Base):
    """Logged collision / high-risk event."""
    __tablename__ = "collision_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    vehicle_a = Column(String(64), nullable=False, index=True)
    vehicle_b = Column(String(64), nullable=True)
    risk_level = Column(String(8), nullable=False)        # LOW / MEDIUM / HIGH
    risk_score = Column(Float, default=0.0)
    ttc_seconds = Column(Float, nullable=True)
    distance_m = Column(Float, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    details = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)


class User(Base):
    """Dashboard / API user accounts."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), unique=True, nullable=False)
    email = Column(String(256), unique=True, nullable=True)
    password_hash = Column(String(256), nullable=True)  # nullable for Google OAuth users
    auth_provider = Column(String(16), default="local")  # local / google
    role = Column(String(16), default="viewer")           # admin / operator / viewer / device
    name = Column(String(128), default="")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    """Security audit trail."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), nullable=False)
    action = Column(String(64), nullable=False)
    resource = Column(String(128), default="")
    details = Column(Text, default="")
    ip_address = Column(String(45), default="")
    created_at = Column(DateTime, default=datetime.utcnow)
