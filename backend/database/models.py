from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, DateTime, ForeignKey, Float, Boolean, Text
from datetime import datetime
from typing import List, Optional

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(100), nullable=True)
    role: Mapped[str] = mapped_column(String(20), default="viewer")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    vehicles: Mapped[List["Vehicle"]] = relationship(back_populates="owner", cascade="all, delete-orphan")

class Vehicle(Base):
    __tablename__ = "vehicles"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    vin: Mapped[Optional[str]] = mapped_column(String(50), unique=True, nullable=True)
    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    owner: Mapped["User"] = relationship(back_populates="vehicles")
    telemetry_records: Mapped[List["TelemetryRecord"]] = relationship(back_populates="vehicle", cascade="all, delete-orphan")

class TelemetryRecord(Base):
    __tablename__ = "telemetry_records"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(Integer, ForeignKey("vehicles.id"))
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    speed: Mapped[float] = mapped_column(Float)
    heading: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    acceleration: Mapped[float] = mapped_column(Float, default=0.0)
    
    vehicle: Mapped["Vehicle"] = relationship(back_populates="telemetry_records")
    risk_results: Mapped[List["RiskAnalysisResult"]] = relationship(back_populates="telemetry", cascade="all, delete-orphan")

class RiskAnalysisResult(Base):
    __tablename__ = "risk_analysis_results"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telemetry_id: Mapped[int] = mapped_column(Integer, ForeignKey("telemetry_records.id"))
    risk_score: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(20)) # SAFE, WARNING, DANGER
    threat_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    telemetry: Mapped["TelemetryRecord"] = relationship(back_populates="risk_results")

class SimulationRun(Base):
    __tablename__ = "simulation_runs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    start_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    vehicle_count: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
