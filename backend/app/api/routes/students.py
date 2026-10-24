from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_parent
from app.models.event import Event
from app.models.student import Student
from app.models.parent_student import ParentStudent

router = APIRouter(tags=["Students"])


@router.get("/students/{student_id}/status")
def get_student_status(student_id: int, current_parent=Depends(require_parent), db: Session = Depends(get_db)):
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
    if not db.query(ParentStudent).filter_by(
        parent_id=current_parent.id, student_id=student_id
    ).first():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Student not linked to parent")

    latest_event = db.query(Event).filter(Event.student_id == student_id).order_by(Event.event_time.desc()).first()
    return {
        "student_id": student.id,
        "status": "ON_BUS" if latest_event and latest_event.event_type.value == "BOARDED" else "OFF_BUS",
        "last_event": latest_event.event_type.value if latest_event else None,
        "last_seen_at": latest_event.event_time if latest_event else None,
    }


@router.get("/students/{student_id}/events")
def list_student_events(
    student_id: int,
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = None,
    current_parent=Depends(require_parent),
    db: Session = Depends(get_db),
):
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
    if not db.query(ParentStudent).filter_by(
        parent_id=current_parent.id, student_id=student_id
    ).first():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Student not linked to parent")

    query = db.query(Event).filter(Event.student_id == student_id)
    if from_:
        query = query.filter(Event.event_time >= (from_.astimezone(timezone.utc).replace(tzinfo=None) if from_.tzinfo else from_))
    if to:
        query = query.filter(Event.event_time <= (to.astimezone(timezone.utc).replace(tzinfo=None) if to.tzinfo else to))
    events = query.order_by(Event.event_time.desc(), Event.id.desc()).all()
    return [{"id": event.id, "student_id": event.student_id, "bus_id": event.bus_id,
             "event_type": event.event_type.value,
             "event_time": (event.event_time.replace(tzinfo=timezone.utc)
                            if event.event_time.tzinfo is None else event.event_time).isoformat(),
             "lat": event.lat, "lng": event.lng, "confidence": event.confidence,
             "source": event.source, "received_at": event.received_at.isoformat() + "Z" if event.received_at else None,
             "gps_status": event.gps_status, "is_delayed": event.is_delayed,
             "direction_source": event.direction_source} for event in events]
