"""Database service layer for Smart Grid API."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_

from production.database.models import (
    User, SmartMeter, Alert, FCMToken, BlockchainLedger, AuditLog
)


class DatabaseService:
    """Service layer for all database operations."""

    @staticmethod
    def create_or_update_alert(
        db: Session,
        bus_id: int,
        alert_type: str,
        attack_type: str,
        confidence: float,
        severity: str,
        description: str
    ) -> Alert:
        """Create a new alert."""
        alert = Alert(
            bus_id=bus_id,
            alert_type=alert_type,
            attack_type=attack_type,
            confidence=confidence,
            severity=severity,
            description=description,
            is_resolved=False,
            created_at=datetime.utcnow()
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)
        return alert

    @staticmethod
    def get_active_alerts(db: Session, limit: int = 100) -> List[Alert]:
        """Get all unresolved alerts."""
        return db.query(Alert).filter(
            Alert.is_resolved == False
        ).order_by(desc(Alert.created_at)).limit(limit).all()

    @staticmethod
    def get_alerts_by_bus(db: Session, bus_id: int) -> List[Alert]:
        """Get all alerts for a specific bus."""
        return db.query(Alert).filter(
            Alert.bus_id == bus_id
        ).order_by(desc(Alert.created_at)).all()

    @staticmethod
    def resolve_alert(db: Session, alert_id: int) -> Optional[Alert]:
        """Mark alert as resolved."""
        alert = db.query(Alert).filter(Alert.id == alert_id).first()
        if alert:
            alert.is_resolved = True
            alert.resolved_at = datetime.utcnow()
            db.commit()
            db.refresh(alert)
        return alert

    @staticmethod
    def register_fcm_token(
        db: Session,
        username: str,
        token: str,
        device_name: Optional[str] = None
    ) -> FCMToken:
        """Register or update FCM token."""
        existing = db.query(FCMToken).filter(FCMToken.token == token).first()
        if existing:
            existing.last_used = datetime.utcnow()
            existing.is_active = True
            db.commit()
            db.refresh(existing)
            return existing

        fcm = FCMToken(
            username=username,
            token=token,
            device_name=device_name or "Unknown",
            is_active=True,
            created_at=datetime.utcnow()
        )
        db.add(fcm)
        db.commit()
        db.refresh(fcm)
        return fcm

    @staticmethod
    def get_active_fcm_tokens(db: Session, username: Optional[str] = None) -> List[FCMToken]:
        """Get all active FCM tokens."""
        query = db.query(FCMToken).filter(FCMToken.is_active == True)
        if username:
            query = query.filter(FCMToken.username == username)
        return query.all()

    @staticmethod
    def update_smart_meter(
        db: Session,
        bus_id: int,
        voltage: Optional[float] = None,
        current: Optional[float] = None,
        power: Optional[float] = None,
        frequency: Optional[float] = None,
        status: Optional[str] = None
    ) -> Optional[SmartMeter]:
        """Update smart meter reading."""
        meter = db.query(SmartMeter).filter(SmartMeter.bus_id == bus_id).first()
        if not meter:
            return None

        if voltage is not None:
            meter.voltage = voltage
        if current is not None:
            meter.current = current
        if power is not None:
            meter.power = power
        if frequency is not None:
            meter.frequency = frequency
        if status is not None:
            meter.status = status

        meter.last_reading = datetime.utcnow()
        db.commit()
        db.refresh(meter)
        return meter

    @staticmethod
    def get_smart_meter(db: Session, bus_id: int) -> Optional[SmartMeter]:
        """Get smart meter by bus_id."""
        return db.query(SmartMeter).filter(SmartMeter.bus_id == bus_id).first()

    @staticmethod
    def get_all_smart_meters(db: Session) -> List[SmartMeter]:
        """Get all smart meters."""
        return db.query(SmartMeter).all()

    @staticmethod
    def create_audit_log(
        db: Session,
        username: Optional[str],
        action: str,
        resource: str,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        status_code: Optional[int] = None
    ) -> AuditLog:
        """Create audit log entry."""
        log = AuditLog(
            username=username,
            action=action,
            resource=resource,
            details=details or {},
            ip_address=ip_address,
            status_code=status_code,
            created_at=datetime.utcnow()
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return log

    @staticmethod
    def create_blockchain_entry(
        db: Session,
        block_number: int,
        timestamp: datetime,
        data: Dict[str, Any],
        hash_val: str,
        previous_hash: Optional[str] = None,
        is_verified: bool = False
    ) -> BlockchainLedger:
        """Create blockchain ledger entry."""
        entry = BlockchainLedger(
            block_number=block_number,
            timestamp=timestamp,
            data=data,
            hash=hash_val,
            previous_hash=previous_hash,
            is_verified=is_verified,
            created_at=datetime.utcnow()
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry

    @staticmethod
    def get_blockchain_entries(db: Session, limit: int = 100) -> List[BlockchainLedger]:
        """Get blockchain entries."""
        return db.query(BlockchainLedger).order_by(
            desc(BlockchainLedger.block_number)
        ).limit(limit).all()

    @staticmethod
    def get_user_by_username(db: Session, username: str) -> Optional[User]:
        """Get user by username."""
        return db.query(User).filter(User.username == username).first()

    @staticmethod
    def get_all_users(db: Session) -> List[User]:
        """Get all users."""
        return db.query(User).all()
