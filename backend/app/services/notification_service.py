import json
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.notification import Notification
from app.models.parent import Parent
from app.models.student import Student

settings = get_settings()


def _sms_client():
    if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
        return None
    from twilio.rest import Client

    return Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)


def _fcm_client():
    try:
        import firebase_admin
        from firebase_admin import credentials, messaging
    except Exception:
        return None, None

    if not firebase_admin._apps:
        try:
            creds = credentials.Certificate(json.loads(settings.FCM_CREDENTIALS_JSON))
            firebase_admin.initialize_app(creds, {"projectId": settings.FCM_PROJECT_ID})
        except Exception:
            return None, None
    return firebase_admin, messaging


def log_notification(db: Session, parent: Parent, student: Student, channel: str, status: str, provider_response: str | None = None) -> Notification:
    notification = Notification(parent_id=parent.id, student_id=student.id, channel=channel, status=status, provider_response=provider_response)
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def send_event_notifications(db: Session, parent: Parent, student: Student, event_type: str, event_id: int, bus_id: int, event_time: datetime) -> None:
    event_time_label = event_time.strftime("%I:%M %p")
    title = "Bus Alert"
    body = f"{student.name} {('boarded' if event_type == 'BOARDED' else 'alighted')} the bus at {event_time_label}"
    payload = {
        "title": title,
        "body": body,
        "data": {
            "student_id": str(student.id),
            "bus_id": str(bus_id),
            "event_type": event_type,
            "event_id": str(event_id),
        },
    }

    firebase_admin, messaging = _fcm_client()
    device_tokens = [
        token.strip() for token in [getattr(parent, "fcm_token", "")] if isinstance(token, str) and token.strip()
    ]

    if firebase_admin and messaging and device_tokens:
        try:
            message = messaging.Message(
                notification=messaging.Notification(title=title, body=body),
                data=payload["data"],
                token=device_tokens[0],
            )
            response = messaging.send(message)
            log_notification(db, parent, student, "PUSH", "SENT", response)
            return
        except Exception as exc:  # fallback to SMS on error
            log_notification(db, parent, student, "PUSH", "FAILED", str(exc))

    client = _sms_client()
    if client and parent.phone:
        try:
            resp = client.messages.create(
                body=f"{student.name} {('boarded' if event_type == 'BOARDED' else 'alighted')} the bus at {event_time_label}.",
                from_=settings.TWILIO_FROM_NUMBER,
                to=parent.phone,
            )
            log_notification(db, parent, student, "SMS", "SENT", str(resp.sid))
            return
        except Exception as exc:
            log_notification(db, parent, student, "SMS", "FAILED", str(exc))
            return

    log_notification(db, parent, student, "SMS", "FAILED", "No push token or SMS provider configured")


def notify_parents_for_event(db: Session, student: Student, bus_id: int, event_type: str, event_id: int, event_time: datetime) -> None:
    for link in student.student_links:
        parent = link.parent
        send_event_notifications(db, parent, student, event_type, event_id, bus_id, event_time)
