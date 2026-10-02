from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_parent
from app.models.event import Event
from app.models.student import Student

router = APIRouter(tags=["Students"])


@router.get("/students/{student_id}/status")
def get_student_status(student_id: int, current_parent=Depends(require_parent), db: Session = Depends(get_db)):
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
    if student not in current_parent.students:
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
    if student not in current_parent.students:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Student not linked to parent")

    query = db.query(Event).filter(Event.student_id == student_id)
    if from_:
        query = query.filter(Event.event_time >= from_)
    if to:
        query = query.filter(Event.event_time <= to)
    return query.order_by(Event.event_time.desc()).all()
