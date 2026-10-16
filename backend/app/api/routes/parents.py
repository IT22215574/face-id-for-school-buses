from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.api.deps import get_db, require_parent
from app.models.parent import Parent
from app.models.student import Student
from app.schemas.parent import ParentOut, ProfileUpdate
from app.schemas.student import StudentOut

router = APIRouter(tags=["Parents"])


@router.get("/me", response_model=ParentOut)
def read_me(current_parent: Parent = Depends(require_parent)):
    return current_parent


@router.get("/me/students", response_model=list[StudentOut])
def read_my_students(current_parent: Parent = Depends(require_parent), db: Session = Depends(get_db)):
    return current_parent.students


@router.get("/me/transport")
def read_my_transport(current_parent: Parent = Depends(require_parent), db: Session = Depends(get_db)):
    from app.models.parent_student import ParentStudent
    from app.models.student_transport import StudentTransport
    from app.models.bus import Bus
    from app.models.payroll import Driver
    from app.models.event import Event
    from app.services.transport_service import SCHOOLS
    query = db.query(Student)
    if current_parent.role == "DRIVER":
        query = query.join(StudentTransport).join(Driver, Driver.bus_id == StudentTransport.bus_id).filter(
            Driver.user_id == current_parent.id, Driver.status == "ACTIVE")
    else:
        query = query.join(ParentStudent).filter(ParentStudent.parent_id == current_parent.id)
    result = []
    for student in query.order_by(Student.id).all():
        assignment = db.get(StudentTransport, student.id)
        bus = db.get(Bus, assignment.bus_id) if assignment else None
        driver = db.query(Driver).filter_by(bus_id=bus.id, status="ACTIVE").first() if bus else None
        latest_event = db.query(Event).filter_by(student_id=student.id).order_by(Event.event_time.desc(), Event.id.desc()).first()
        guardian = student.parents[0] if student.parents else None
        result.append({"id": student.id, "name": student.name, "grade": student.grade,
            "school": SCHOOLS.get(student.school_id, {"name": student.school_id}),
            "bus_id": bus.id if bus else None, "plate_no": bus.plate_no if bus else None,
            "route_name": bus.route_name if bus else None,
            "driver_name": driver.name if driver else None, "driver_phone": driver.phone if driver else None,
            "present": bool(latest_event and latest_event.event_type.value == "BOARDED"),
            "parent": guardian.name if guardian else "", "phone": guardian.phone if guardian else ""})
    return result


@router.patch("/me", response_model=ParentOut)
def update_me(payload: ProfileUpdate, current_parent: Parent = Depends(require_parent), db: Session = Depends(get_db)):
    account = db.get(Parent, current_parent.id)
    if account is None:
        raise HTTPException(status_code=401, detail="Account not found")
    account.name = payload.name
    account.phone = payload.phone
    account.email = str(payload.email)
    # Keep the contact information shown to parents in sync with the driver account.
    if account.role == "DRIVER":
        from app.models.payroll import Driver
        with db.no_autoflush:
            for driver in db.query(Driver).filter_by(user_id=account.id).all():
                driver.name = account.name
                driver.phone = account.phone
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email or phone is already in use")
    db.refresh(account)
    return account
