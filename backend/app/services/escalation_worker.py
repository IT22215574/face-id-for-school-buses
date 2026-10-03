from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.emergency import EmergencyAlert, EmergencyContact, EmergencyNotification
from app.models.parent import Parent


def escalate_unacknowledged_alerts(db: Session, escalation_seconds: int = 60) -> list[int]:
    alerts = db.query(EmergencyAlert).filter(EmergencyAlert.status.in_(["OPEN", "RESPONDING"]))
    escalated_ids: list[int] = []
    for alert in alerts:
        if alert.acknowledged_at is not None:
            continue
        if datetime.now(timezone.utc) - alert.created_at < timedelta(seconds=escalation_seconds):
            continue
        attempts = db.query(EmergencyNotification).filter(EmergencyNotification.alert_id == alert.id).count()
        if attempts == 0:
            admins = db.query(Parent).filter(Parent.role.in_(["ADMIN", "COORDINATOR"]))
            for admin in admins:
                db.add(
                    EmergencyNotification(
                        alert_id=alert.id, recipient_user_id=admin.id, recipient_phone=admin.phone, channel="PUSH", status="SENT", attempt_no=1, provider_response="Escalated pending alert"
                    )
                )
            escalated_ids.append(alert.id)
            continue
        contacts = db.query(EmergencyContact).order_by(EmergencyContact.priority_order.asc()).all()
        for contact in contacts:
            if attempts < len(contacts) + 1:
                db.add(
                    EmergencyNotification(
                        alert_id=alert.id, recipient_phone=contact.phone, channel="SMS", status="SENT", attempt_no=attempts + 1, provider_response=f"Escalation to {contact.name}"
                    )
                )
                break
        escalated_ids.append(alert.id)
    db.commit()
    return escalated_ids
