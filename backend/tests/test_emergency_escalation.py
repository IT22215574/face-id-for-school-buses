from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.db.base import Base
from app.models.emergency import EmergencyAlert, EmergencyNotification
from app.models.parent import Parent
from app.services.escalation_worker import escalate_unacknowledged_alerts

settings = get_settings()
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def test_escalation_creates_notification_after_threshold():
    db = SessionLocal()
    Base.metadata.create_all(bind=engine)
    try:
        admin = Parent(name="Admin", phone="+10000000010", email="adminescalate@example.com", password_hash="x", role="ADMIN")
        db.add(admin)
        db.commit()
        db.refresh(admin)

        driver = Parent(name="Driver", phone="+10000000011", email="driverescalate@example.com", password_hash="x", role="DRIVER")
        db.add(driver)
        db.commit()
        db.refresh(driver)

        alert = EmergencyAlert(
            bus_id=1,
            driver_id=None,
            triggered_by_user_id=driver.id,
            type="SOS",
            severity="CRITICAL",
            status="OPEN",
            lat=6.9,
            lng=79.9,
            message="SOS",
            source="DRIVER_APP",
            created_at=datetime.now(timezone.utc) - timedelta(seconds=65),
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)

        ids = escalate_unacknowledged_alerts(db, escalation_seconds=60)

        assert alert.id in ids
        assert db.query(EmergencyNotification).filter(EmergencyNotification.alert_id == alert.id).count() >= 1
    finally:
        db.close()
