from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_admin_or_coordinator, require_parent
from app.core.security import hash_api_key
from app.db.session import SessionLocal
from app.models.bus import Bus
from app.models.bus_location import BusLocation
from app.models.device import Device
from app.models.emergency import EmergencyAlert, EmergencyAlertUpdate, EmergencyContact, EmergencyNotification
from app.models.parent import Parent
from app.models.parent_student import ParentStudent
from app.models.payroll import Driver
from app.models.student import Student
from app.services.emergency_service import EmergencyService, emergency_alert_filter, get_active_alerts

router = APIRouter(tags=["Emergency"])


class EmergencyTriggerIn(BaseModel):
    bus_id: int | None = None
    type: str = Field(default="SOS")
    message: str | None = None
    lat: float | None = None
    lng: float | None = None


class EmergencyCancelIn(BaseModel):
    reason: str = Field(..., min_length=3)


class EmergencyUpdateIn(BaseModel):
    status: str = Field(...)
    note: str | None = None


class EmergencyContactIn(BaseModel):
    school_id: str
    name: str
    phone: str
    role: str = "COORDINATOR"
    priority_order: int = 1


@router.post("/emergency/trigger", status_code=status.HTTP_201_CREATED)
def trigger_emergency(payload: EmergencyTriggerIn, db: Session = Depends(get_db), current_user: Parent = Depends(require_parent)):
    return EmergencyService.trigger_alert(db, current_user, payload.model_dump())


@router.post("/emergency/{alert_id}/cancel")
def cancel_emergency(alert_id: int, payload: EmergencyCancelIn, db: Session = Depends(get_db), current_user: Parent = Depends(require_parent)):
    return EmergencyService.cancel_alert(db, current_user, alert_id, payload.reason)


@router.get("/emergency/active")
def get_active_emergency_alerts(db: Session = Depends(get_db), current_user: Parent = Depends(require_parent)):
    return get_active_alerts(db, current_user)


@router.get("/admin/emergency")
def list_admin_alerts(
    db: Session = Depends(get_db),
    current_user: Parent = Depends(require_admin_or_coordinator),
    status: str | None = Query(default=None),
    bus_id: int | None = Query(default=None),
    from_: str | None = Query(default=None, alias="from"),
    to: str | None = Query(default=None),
):
    query = db.query(EmergencyAlert)
    if status:
        query = query.filter(EmergencyAlert.status == status)
    if bus_id:
        query = query.filter(EmergencyAlert.bus_id == bus_id)
    if from_:
        start = datetime.fromisoformat(from_)
        query = query.filter(EmergencyAlert.created_at >= start)
    if to:
        end = datetime.fromisoformat(to)
        query = query.filter(EmergencyAlert.created_at <= end)
    return query.order_by(EmergencyAlert.created_at.desc()).all()


@router.post("/admin/emergency/{alert_id}/acknowledge")
def acknowledge_alert(alert_id: int, db: Session = Depends(get_db), current_user: Parent = Depends(require_admin_or_coordinator)):
    return EmergencyService.acknowledge_alert(db, current_user, alert_id)


@router.post("/admin/emergency/{alert_id}/update")
def update_alert(alert_id: int, payload: EmergencyUpdateIn, db: Session = Depends(get_db), current_user: Parent = Depends(require_admin_or_coordinator)):
    return EmergencyService.update_alert(db, current_user, alert_id, payload.status, payload.note)


@router.post("/admin/emergency/{alert_id}/resolve")
def resolve_alert(alert_id: int, db: Session = Depends(get_db), current_user: Parent = Depends(require_admin_or_coordinator)):
    return EmergencyService.resolve_alert(db, current_user, alert_id)


@router.get("/admin/emergency-contacts")
def list_contacts(db: Session = Depends(get_db), current_user: Parent = Depends(require_admin_or_coordinator)):
    return db.query(EmergencyContact).order_by(EmergencyContact.priority_order.asc(), EmergencyContact.id.asc()).all()


@router.post("/admin/emergency-contacts", status_code=status.HTTP_201_CREATED)
def create_contact(payload: EmergencyContactIn, db: Session = Depends(get_db), current_user: Parent = Depends(require_admin_or_coordinator)):
    contact = EmergencyContact(
        school_id=payload.school_id,
        name=payload.name,
        phone=payload.phone,
        role=payload.role,
        priority_order=payload.priority_order,
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


@router.put("/admin/emergency-contacts/{contact_id}")
def update_contact(contact_id: int, payload: EmergencyContactIn, db: Session = Depends(get_db), current_user: Parent = Depends(require_admin_or_coordinator)):
    contact = db.get(EmergencyContact, contact_id)
    if contact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emergency contact not found")
    contact.school_id = payload.school_id
    contact.name = payload.name
    contact.phone = payload.phone
    contact.role = payload.role
    contact.priority_order = payload.priority_order
    db.commit()
    db.refresh(contact)
    return contact


@router.delete("/admin/emergency-contacts/{contact_id}")
def delete_contact(contact_id: int, db: Session = Depends(get_db), current_user: Parent = Depends(require_admin_or_coordinator)):
    contact = db.get(EmergencyContact, contact_id)
    if contact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emergency contact not found")
    db.delete(contact)
    db.commit()
    return {"message": "Emergency contact deleted"}


@router.post("/device/emergency", status_code=status.HTTP_201_CREATED)
def device_emergency_trigger(
    payload: EmergencyTriggerIn,
    x_api_key: str = Header(default="", alias="x-api-key"),
    db: Session = Depends(get_db),
):
    if not x_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Device API key required")
    device = db.query(Device).filter(Device.api_key_hash == hash_api_key(x_api_key)).first()
    if device is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid device API key")
    alert = EmergencyService.trigger_alert(db, Parent(id=0, role="DEVICE", name="Device", phone="", email="device@local"), payload.model_dump(), bus_id=device.bus_id, source="DEVICE_BUTTON")
    return alert


@router.websocket("/ws/admin/emergency")
async def admin_emergency_ws(websocket):
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    try:
        from jose import jwt
        from app.core.config import get_settings

        payload = jwt.decode(token, get_settings().JWT_SECRET, algorithms=["HS256"])
        if payload.get("type") != "access":
            raise ValueError("Token type invalid")
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    from app.api.routes.ws import manager

    manager.admin_connections.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except Exception:
        manager.admin_connections = [conn for conn in manager.admin_connections if conn is not websocket]
