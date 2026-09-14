"""SQLAlchemy ORM models for Smart Grid database."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255))
    role = Column(String(50), default="viewer", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    fcm_tokens = relationship("FCMToken", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")


class SmartMeter(Base):
    __tablename__ = "smart_meters"

    id = Column(Integer, primary_key=True)
    bus_id = Column(Integer, unique=True, nullable=False)
    voltage = Column(Float)
    current = Column(Float)
    power = Column(Float)
    frequency = Column(Float)
    status = Column(String(50), default="online")
    consumer_type = Column(String(100))
    last_reading = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    alerts = relationship("Alert", back_populates="meter")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True)
    bus_id = Column(Integer, ForeignKey("smart_meters.bus_id", ondelete="CASCADE"), nullable=False)
    alert_type = Column(String(100), nullable=False)
    attack_type = Column(String(50))
    confidence = Column(Float, nullable=False)
    severity = Column(String(50), nullable=False)
    description = Column(Text)
    is_resolved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime)

    meter = relationship("SmartMeter", back_populates="alerts")


class FCMToken(Base):
    __tablename__ = "fcm_tokens"

    id = Column(Integer, primary_key=True)
    username = Column(String(255), ForeignKey("users.username", ondelete="CASCADE"), nullable=False)
    token = Column(String(255), unique=True, nullable=False)
    device_name = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used = Column(DateTime)

    user = relationship("User", back_populates="fcm_tokens")


class BlockchainLedger(Base):
    __tablename__ = "blockchain_ledger"

    id = Column(Integer, primary_key=True)
    block_number = Column(Integer, unique=True, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    data = Column(JSON)
    hash = Column(String(255), unique=True, nullable=False)
    previous_hash = Column(String(255))
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True)
    username = Column(String(255), ForeignKey("users.username", ondelete="SET NULL"))
    action = Column(String(255))
    resource = Column(String(255))
    details = Column(JSON)
    ip_address = Column(String(45))
    status_code = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="audit_logs")
