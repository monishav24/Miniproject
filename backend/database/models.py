from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, DateTime, ForeignKey, Float
from datetime import datetime
from typing import List, Optional

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    vehicles: Mapped[List["Vehicle"]] = relationship(back_populates="owner", cascade="all, delete-orphan")

class Vehicle(Base):
    __tablename__ = "vehicles"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    vin: Mapped[Optional[str]] = mapped_column(String(50), unique=True, nullable=True)
    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    owner: Mapped["User"] = relationship(back_populates="vehicles")
    telemetry: Mapped[List["Telemetry"]] = relationship(back_populates="vehicle", cascade="all, delete-orphan")

class Telemetry(Base):
    __tablename__ = "telemetry"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(Integer, ForeignKey("vehicles.id"))
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    speed: Mapped[float] = mapped_column(Float)
    heading: Mapped[float] = mapped_column(Float)
    
    # AI Scores
    collision_probability: Mapped[float] = mapped_column(Float, default=0.0)
    unsafe_score: Mapped[float] = mapped_column(Float, default=0.0)
    
    vehicle: Mapped["Vehicle"] = relationship(back_populates="telemetry")
