from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.api.deps import get_db, require_parent
from app.models.bus import Bus
from app.models.bus_location import BusLocation
from app.models.payroll import Driver
from app.services.device_service import save_bus_location
from app.services.bus_service import get_live_location, get_route_history

from app.services.transport_service import authorize_bus, ROUTE

router = APIRouter(tags=["Buses"])


class PhoneLocationIn(BaseModel):
    lat: float = Field(ge=-90, le=90, allow_inf_nan=False)
    lng: float = Field(ge=-180, le=180, allow_inf_nan=False)
    speed: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    heading: float | None = Field(default=None, ge=0, lt=360, allow_inf_nan=False)
    gps_time: datetime


def assigned_driver_bus(user, db: Session) -> Bus:
    if user.role != "DRIVER":
        raise HTTPException(status_code=403, detail="Driver access required")
    driver = db.query(Driver).filter(Driver.user_id == user.id, Driver.status == "ACTIVE").first()
    bus = db.get(Bus, driver.bus_id) if driver and driver.bus_id else None
    if bus is None:
        raise HTTPException(status_code=403, detail="No active bus assignment. Contact your school.")
    return bus


@router.get("/driver/bus")
def read_driver_bus(current_user=Depends(require_parent), db: Session = Depends(get_db)):
    bus = assigned_driver_bus(current_user, db)
    return {"id": bus.id, "plate_no": bus.plate_no, "route_name": bus.route_name}


@router.post("/driver/location")
def share_phone_location(payload: PhoneLocationIn, current_user=Depends(require_parent), db: Session = Depends(get_db)):
    bus = assigned_driver_bus(current_user, db)
    location = save_bus_location(db, bus.id, payload.lat, payload.lng, payload.speed, payload.heading, payload.gps_time)
    return {"location_id": location.id, "bus_id": bus.id, "server_time": location.server_time}


@router.get("/buses/{bus_id}/live-location")
def read_bus_live_location(bus_id: int, current_parent=Depends(require_parent), db: Session = Depends(get_db)):
    bus = db.get(Bus, bus_id)
    if bus is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bus not found")
    authorize_bus(db, current_parent, bus_id)
    location = get_live_location(db, bus_id)
    if location is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No live location available")
    return location


@router.get("/buses/{bus_id}/route-history")
def read_route_history(
    bus_id: int,
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = None,
    current_parent=Depends(require_parent),
    db: Session = Depends(get_db),
):
    bus = db.get(Bus, bus_id)
    if bus is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bus not found")
    authorize_bus(db, current_parent, bus_id)
    points = get_route_history(db, bus_id, from_, to)
    return {"bus_id": bus_id, "points": points}


@router.get("/buses/{bus_id}/route")
def read_bus_route(bus_id: int, current_parent=Depends(require_parent), db: Session = Depends(get_db)):
    authorize_bus(db, current_parent, bus_id)
    bus = db.get(Bus, bus_id)
    return {"bus_id": bus_id, "name": bus.route_name, "sample": True,
            "stops": ROUTE if bus.route_name.startswith("Kurunegala") else []}


class DriverStudentIn(BaseModel):
    model_config = {"str_strip_whitespace": True, "extra": "forbid"}

    name: str = Field(min_length=2, max_length=120)
    grade: str = Field(min_length=1, max_length=30)
    school_id: str = Field(min_length=1, max_length=80)
    parent_email: str = Field(min_length=3, max_length=255)
    father_phone: str = Field(default="", max_length=32, pattern=r"^(?:|\+?[0-9][0-9 ()-]{6,30}[0-9])$")
    mother_phone: str = Field(default="", max_length=32, pattern=r"^(?:|\+?[0-9][0-9 ()-]{6,30}[0-9])$")


@router.post("/driver/students", status_code=status.HTTP_201_CREATED)
def add_driver_student(payload: DriverStudentIn, current_user=Depends(require_parent), db: Session = Depends(get_db)):
    from app.models.parent import Parent
    from app.models.student import Student
    from app.models.parent_student import ParentStudent
    from app.models.student_transport import StudentTransport
    from app.services.transport_service import SCHOOLS

    bus = assigned_driver_bus(current_user, db)
    if payload.school_id not in SCHOOLS:
        raise HTTPException(status_code=422, detail="Choose a supported school")
    parent = db.query(Parent).filter(Parent.email == payload.parent_email.lower(), Parent.role == "PARENT").first()
    if parent is None:
        raise HTTPException(status_code=404, detail="No parent account found with that email. Ask the parent to register first.")
    student = Student(name=payload.name, grade=payload.grade, school_id=payload.school_id,
                      father_phone=payload.father_phone, mother_phone=payload.mother_phone)
    try:
        db.add(student)
        db.flush()
        db.add(ParentStudent(parent_id=parent.id, student_id=student.id))
        db.add(StudentTransport(student_id=student.id, bus_id=bus.id))
        db.commit()
        db.refresh(student)
    except Exception:
        db.rollback()
        raise
    return {"id": student.id, "name": student.name, "bus_id": bus.id}
