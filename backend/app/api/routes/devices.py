from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.security import hash_api_key
from app.models.device import Device
from app.models.bus import Bus
from app.models.student import Student
from app.models.student_transport import StudentTransport
from app.models.parent_student import ParentStudent
from app.services.device_service import save_bus_location, save_event, validate_device_api_key
from app.services.notification_service import notify_parents_for_event
from app.schemas.device import DeviceEventIn, DeviceHeartbeat, DeviceLocationIn

router = APIRouter(prefix="/device", tags=["Device"])


def require_device_api_key(x_api_key: str = Header(..., alias="x-api-key"), db: Session = Depends(get_db)) -> Device:
    return validate_device_api_key(db, x_api_key)


@router.post("/events")
def ingest_event(payload: DeviceEventIn, device: Device = Depends(require_device_api_key), db: Session = Depends(get_db)):
    if payload.bus_id != device.bus_id:
        raise HTTPException(status_code=403, detail="Device is not assigned to this bus")
    assignment = db.get(StudentTransport, payload.student_id)
    if assignment is None or assignment.bus_id != device.bus_id:
        raise HTTPException(status_code=403, detail="Student is not assigned to this bus")
    student = db.get(Student, payload.student_id)
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
    bus = db.get(Bus, payload.bus_id)
    if bus is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bus not found")
    event = save_event(db, payload.student_id, payload.bus_id, payload.event_type, payload.event_time.astimezone(timezone.utc), payload.lat, payload.lng, payload.confidence, "DEVICE")
    notify_parents_for_event(db, student, payload.bus_id, payload.event_type.upper(), event.id, payload.event_time)
    return {"message": "Event processed", "event_id": event.id, "status": event.event_type.value}


@router.post("/location")
def ingest_bus_location(payload: DeviceLocationIn, device: Device = Depends(require_device_api_key), db: Session = Depends(get_db)):
    if payload.bus_id != device.bus_id:
        raise HTTPException(status_code=403, detail="Device is not assigned to this bus")
    bus = db.get(Bus, payload.bus_id)
    if bus is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bus not found")
    location = save_bus_location(db, payload.bus_id, payload.lat, payload.lng, payload.speed, payload.heading, payload.gps_time)
    return {"message": "Location processed", "location_id": location.id}


@router.post("/heartbeat")
def device_heartbeat(payload: DeviceHeartbeat, device: Device = Depends(require_device_api_key), db: Session = Depends(get_db)):
    if payload.bus_id != device.bus_id:
        raise HTTPException(status_code=403, detail="Device is not assigned to this bus")
    device.status = payload.status
    device.last_seen_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": "Heartbeat received", "device_id": device.id, "status": device.status}


@router.get("/students")
def device_students(device: Device = Depends(require_device_api_key), db: Session = Depends(get_db)):
    """IDs used when enrolling faces; only the authenticated bus roster is returned."""
    students = db.query(Student).join(StudentTransport).filter(
        StudentTransport.bus_id == device.bus_id).order_by(Student.id).all()
    return {"bus_id": device.bus_id, "students": [
        {"student_id": student.id, "name": student.name, "grade": student.grade}
        for student in students]}
