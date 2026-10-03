from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_api_key
from app.models.bus import Bus
from app.models.bus_location import BusLocation
from app.models.device import Device
from app.models.emergency import EmergencyAlert, EmergencyAlertUpdate, EmergencyContact, EmergencyNotification
from app.models.event import Event
from app.models.parent import Parent
from app.models.parent_student import ParentStudent
from app.models.payroll import Driver
from app.models.student import Student

settings = get_settings()
_TRIGGER_HISTORY: dict[int, list[datetime]] = defaultdict(list)


class EmergencyService:
    @staticmethod
    def _rate_limit_ok(user_id: int, alert_type: str) -> bool:
        if alert_type.upper() in {"SOS", "ACCIDENT", "MEDICAL", "SECURITY"}:
            return True
        now = datetime.now(timezone.utc)
        history = _TRIGGER_HISTORY.get(user_id, [])
        history = [ts for ts in history if now - ts <= timedelta(minutes=10)]
        _TRIGGER_HISTORY[user_id] = history
        return len(history) < 3

    @staticmethod
    def _record_trigger(user_id: int) -> None:
        now = datetime.now(timezone.utc)
        history = _TRIGGER_HISTORY.get(user_id, [])
        history = [ts for ts in history if now - ts <= timedelta(minutes=10)]
        history.append(now)
        _TRIGGER_HISTORY[user_id] = history

    @staticmethod
    def _send_push_message(recipient: Parent, title: str, body: str, data: dict[str, str]) -> None:
        if not recipient.fcm_token:
            return
        try:
            import firebase_admin
            from firebase_admin import messaging

            if not firebase_admin._apps:
                from firebase_admin import credentials
                import json

                creds = credentials.Certificate(json.loads(settings.FCM_CREDENTIALS_JSON))
                firebase_admin.initialize_app(creds, {"projectId": settings.FCM_PROJECT_ID})

            message = messaging.Message(
                notification=messaging.Notification(title=title, body=body),
                data=data,
                token=recipient.fcm_token,
            )
            messaging.send(message)
        except Exception:
            pass

    @staticmethod
    def _send_sms_message(phone: str, body: str) -> None:
        if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN or not settings.TWILIO_FROM_NUMBER:
            return
        try:
            from twilio.rest import Client

            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            client.messages.create(body=body, from_=settings.TWILIO_FROM_NUMBER, to=phone)
        except Exception:
            pass

    @staticmethod
    def _log_notification(db: Session, alert: EmergencyAlert, recipient_user_id: int | None, phone: str | None, channel: str, status: str, attempt_no: int = 1, response: str | None = None) -> EmergencyNotification:
        note = EmergencyNotification(
            alert_id=alert.id,
            recipient_user_id=recipient_user_id,
            recipient_phone=phone,
            channel=channel,
            status=status,
            attempt_no=attempt_no,
            provider_response=response,
        )
        db.add(note)
        db.commit()
        db.refresh(note)
        return note

    @staticmethod
    def _notify_admins_and_parents(db: Session, alert: EmergencyAlert) -> None:
        admins = db.query(Parent).filter(Parent.role.in_(["ADMIN", "COORDINATOR"]))
        for admin in admins:
            title = "Emergency Alert"
            body = f"Bus {alert.bus_id} reported a {alert.type}."
            data = {"alert_id": str(alert.id), "status": alert.status, "severity": alert.severity}
            EmergencyService._send_push_message(admin, title, body, data)
            EmergencyService._send_sms_message(admin.phone, f"Emergency on bus {alert.bus_id}: {alert.type}. Please acknowledge immediately.")
            EmergencyService._log_notification(db, alert, admin.id, admin.phone, "PUSH", "SENT", 1, body)
            EmergencyService._log_notification(db, alert, admin.id, admin.phone, "SMS", "SENT", 1, "Emergency alert")

        bus = db.get(Bus, alert.bus_id)
        students_on_bus = EmergencyService._students_on_bus(db, alert.bus_id)
        student_ids = [student.id for student in students_on_bus]
        if not student_ids:
            return
        parent_links = db.query(ParentStudent).filter(ParentStudent.student_id.in_(student_ids)).all()
        parents = []
        for link in parent_links:
            parent = db.get(Parent, link.parent_id)
            if parent and parent.id not in {p.id for p in parents}:
                parents.append(parent)
        for parent in parents:
            title = "Bus update"
            body = f"Bus {bus.plate_no if bus else alert.bus_id} has reported an issue. The school has been alerted. Track live location in the app."
            data = {"alert_id": str(alert.id), "bus_id": str(alert.bus_id), "type": alert.type}
            EmergencyService._send_push_message(parent, title, body, data)
            EmergencyService._send_sms_message(parent.phone, body)
            EmergencyService._log_notification(db, alert, parent.id, parent.phone, "PUSH", "SENT", 1, body)
            EmergencyService._log_notification(db, alert, parent.id, parent.phone, "SMS", "SENT", 1, body)

    @staticmethod
    def _students_on_bus(db: Session, bus_id: int) -> list[Student]:
        latest_events = db.query(Event).filter(Event.bus_id == bus_id).all()
        latest_by_student: dict[int, Event] = {}
        for event in latest_events:
            current = latest_by_student.get(event.student_id)
            if current is None or event.event_time > current.event_time:
                latest_by_student[event.student_id] = event
        students = []
        for event in latest_by_student.values():
            if event.event_type == "BOARDED":
                student = db.get(Student, event.student_id)
                if student:
                    students.append(student)
        return students

    @staticmethod
    def trigger_alert(db: Session, current_user: Parent, payload: dict[str, Any], bus_id: int | None = None, source: str = "DRIVER_APP") -> EmergencyAlert:
        if not current_user or current_user.id == 0:
            if not bus_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bus ID required for device-triggered alert")
            user_id = db.query(Parent).filter(Parent.role == "ADMIN").first()
            if user_id is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No admin user available")
            current_user = user_id
        if not current_user.role in {"DRIVER", "ATTENDANT", "ADMIN", "COORDINATOR", "PARENT"}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Role not allowed to trigger emergency")
        if bus_id is None:
            driver = db.query(Driver).filter(Driver.user_id == current_user.id).first()
            if driver is not None and driver.bus_id:
                bus_id = driver.bus_id
        if bus_id is None:
            bus_id = int(payload.get("bus_id") or 0)
        if not bus_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A bus must be selected for the emergency alert")
        if not EmergencyService._rate_limit_ok(current_user.id, str(payload.get("type", "SOS")).upper()):
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Emergency trigger rate limit exceeded")

        severity = payload.get("severity") or ("CRITICAL" if str(payload.get("type", "SOS")).upper() in {"SOS", "ACCIDENT", "MEDICAL", "SECURITY"} else "MEDIUM")
        lat = float(payload.get("lat") or 0.0)
        lng = float(payload.get("lng") or 0.0)
        if lat == 0.0 and lng == 0.0:
            latest = db.query(BusLocation).filter(BusLocation.bus_id == bus_id).order_by(BusLocation.server_time.desc()).first()
            if latest:
                lat = latest.lat
                lng = latest.lng
        driver = db.query(Driver).filter(Driver.user_id == current_user.id).first()
        alert = EmergencyAlert(
            bus_id=bus_id,
            driver_id=driver.id if driver else None,
            triggered_by_user_id=current_user.id,
            type=str(payload.get("type", "SOS")).upper(),
            severity=severity,
            status="OPEN",
            lat=lat,
            lng=lng,
            message=payload.get("message"),
            source=source,
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)
        EmergencyService._record_trigger(current_user.id)
        db.add(EmergencyAlertUpdate(alert_id=alert.id, user_id=current_user.id, status="OPEN", note=payload.get("message") or "Emergency triggered"))
        db.commit()
        EmergencyService._notify_admins_and_parents(db, alert)
        return alert

    @staticmethod
    def cancel_alert(db: Session, current_user: Parent, alert_id: int, reason: str) -> dict[str, Any]:
        alert = db.get(EmergencyAlert, alert_id)
        if alert is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
        now = datetime.now(timezone.utc)
        if current_user.role not in {"ADMIN", "COORDINATOR"} and (now - alert.created_at).total_seconds() > 60:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cancel window expired")
        alert.status = "FALSE_ALARM"
        alert.resolution_notes = reason
        alert.resolved_by = current_user.id
        alert.resolved_at = now
        db.add(EmergencyAlertUpdate(alert_id=alert.id, user_id=current_user.id, status="FALSE_ALARM", note=reason))
        db.commit()
        return {"message": "Emergency alert cancelled", "alert_id": alert.id}

    @staticmethod
    def acknowledge_alert(db: Session, current_user: Parent, alert_id: int) -> dict[str, Any]:
        alert = db.get(EmergencyAlert, alert_id)
        if alert is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
        alert.status = "ACKNOWLEDGED"
        alert.acknowledged_by = current_user.id
        alert.acknowledged_at = datetime.now(timezone.utc)
        db.add(EmergencyAlertUpdate(alert_id=alert.id, user_id=current_user.id, status="ACKNOWLEDGED", note="Alert acknowledged"))
        db.commit()
        return {"message": "Alert acknowledged", "alert_id": alert.id}

    @staticmethod
    def update_alert(db: Session, current_user: Parent, alert_id: int, status: str, note: str | None = None) -> dict[str, Any]:
        alert = db.get(EmergencyAlert, alert_id)
        if alert is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
        alert.status = status
        if note:
            alert.resolution_notes = note
        db.add(EmergencyAlertUpdate(alert_id=alert.id, user_id=current_user.id, status=status, note=note))
        db.commit()
        return {"message": "Alert updated", "alert_id": alert.id, "status": status}

    @staticmethod
    def resolve_alert(db: Session, current_user: Parent, alert_id: int) -> dict[str, Any]:
        alert = db.get(EmergencyAlert, alert_id)
        if alert is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
        alert.status = "RESOLVED"
        alert.resolved_by = current_user.id
        alert.resolved_at = datetime.now(timezone.utc)
        db.add(EmergencyAlertUpdate(alert_id=alert.id, user_id=current_user.id, status="RESOLVED", note="Alert resolved"))
        db.commit()
        return {"message": "Alert resolved", "alert_id": alert.id}

    @staticmethod
    def admin_contacts(db: Session) -> list[EmergencyContact]:
        return db.query(EmergencyContact).order_by(EmergencyContact.priority_order.asc()).all()


def emergency_alert_filter(db: Session, status: str | None = None, bus_id: int | None = None, from_dt: datetime | None = None, to_dt: datetime | None = None):
    query = db.query(EmergencyAlert)
    if status:
        query = query.filter(EmergencyAlert.status == status)
    if bus_id:
        query = query.filter(EmergencyAlert.bus_id == bus_id)
    if from_dt:
        query = query.filter(EmergencyAlert.created_at >= from_dt)
    if to_dt:
        query = query.filter(EmergencyAlert.created_at <= to_dt)
    return query.order_by(EmergencyAlert.created_at.desc()).all()


def get_active_alerts(db: Session, current_user: Parent):
    if current_user.role in {"ADMIN", "COORDINATOR"}:
        return db.query(EmergencyAlert).filter(EmergencyAlert.status.in_(["OPEN", "ACKNOWLEDGED", "RESPONDING"]))
    driver = db.query(Driver).filter(Driver.user_id == current_user.id).first()
    if driver:
        return db.query(EmergencyAlert).filter(EmergencyAlert.driver_id == driver.id, EmergencyAlert.status.in_(["OPEN", "ACKNOWLEDGED", "RESPONDING"]))
    return db.query(EmergencyAlert).filter(EmergencyAlert.triggered_by_user_id == current_user.id, EmergencyAlert.status.in_(["OPEN", "ACKNOWLEDGED", "RESPONDING"]))
