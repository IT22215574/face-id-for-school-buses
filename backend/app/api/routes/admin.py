from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_admin
from app.core.security import hash_api_key, hash_password
from app.models.bus import Bus
from app.models.device import Device
from app.models.parent import Parent
from app.models.parent_student import ParentStudent
from app.models.student import Student
from app.schemas.admin import ParentCreate, ParentOut, StudentCreate, StudentOut, BusCreate, BusOut
from app.schemas.parent import ParentStudentLink

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/students", response_model=list[StudentOut])
def list_students(db: Session = Depends(get_db), admin: Parent = Depends(require_admin)):
    return db.query(Student).order_by(Student.created_at.desc()).all()


@router.post("/students", response_model=StudentOut, status_code=status.HTTP_201_CREATED)
def create_student(payload: StudentCreate, db: Session = Depends(get_db), admin: Parent = Depends(require_admin)):
    student = Student(name=payload.name, grade=payload.grade, school_id=payload.school_id)
    db.add(student)
    db.commit()
    db.refresh(student)
    return student


@router.get("/students/{student_id}", response_model=StudentOut)
def get_student(student_id: int, db: Session = Depends(get_db), admin: Parent = Depends(require_admin)):
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
    return student


@router.put("/students/{student_id}", response_model=StudentOut)
def update_student(student_id: int, payload: StudentCreate, db: Session = Depends(get_db), admin: Parent = Depends(require_admin)):
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
    student.name = payload.name
    student.grade = payload.grade
    student.school_id = payload.school_id
    db.commit()
    db.refresh(student)
    return student


@router.delete("/students/{student_id}")
def delete_student(student_id: int, db: Session = Depends(get_db), admin: Parent = Depends(require_admin)):
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
    db.delete(student)
    db.commit()
    return {"message": "Student deleted"}


@router.get("/parents", response_model=list[ParentOut])
def list_parents(db: Session = Depends(get_db), admin: Parent = Depends(require_admin)):
    return db.query(Parent).order_by(Parent.created_at.desc()).all()


@router.post("/parents", response_model=ParentOut, status_code=status.HTTP_201_CREATED)
def create_parent(payload: ParentCreate, db: Session = Depends(get_db), admin: Parent = Depends(require_admin)):
    student = db.query(Parent).filter((Parent.email == payload.email) | (Parent.phone == payload.phone)).first()
    if student:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Parent already exists")
    parent = Parent(name=payload.name, phone=payload.phone, email=payload.email, password_hash=hash_password(payload.password_hash))
    db.add(parent)
    db.commit()
    db.refresh(parent)
    return parent


@router.get("/parents/{parent_id}", response_model=ParentOut)
def get_parent(parent_id: int, db: Session = Depends(get_db), admin: Parent = Depends(require_admin)):
    parent = db.get(Parent, parent_id)
    if parent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parent not found")
    return parent


@router.put("/parents/{parent_id}", response_model=ParentOut)
def update_parent(parent_id: int, payload: ParentCreate, db: Session = Depends(get_db), admin: Parent = Depends(require_admin)):
    parent = db.get(Parent, parent_id)
    if parent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parent not found")
    parent.name = payload.name
    parent.phone = payload.phone
    parent.email = payload.email
    parent.password_hash = hash_password(payload.password_hash)
    db.commit()
    db.refresh(parent)
    return parent


@router.delete("/parents/{parent_id}")
def delete_parent(parent_id: int, db: Session = Depends(get_db), admin: Parent = Depends(require_admin)):
    parent = db.get(Parent, parent_id)
    if parent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parent not found")
    db.delete(parent)
    db.commit()
    return {"message": "Parent deleted"}


@router.get("/buses", response_model=list[BusOut])
def list_buses(db: Session = Depends(get_db), admin: Parent = Depends(require_admin)):
    return db.query(Bus).order_by(Bus.created_at.desc()).all()


@router.post("/buses", response_model=BusOut, status_code=status.HTTP_201_CREATED)
def create_bus(payload: BusCreate, db: Session = Depends(get_db), admin: Parent = Depends(require_admin)):
    bus = Bus(plate_no=payload.plate_no, device_id=payload.device_id, route_name=payload.route_name)
    db.add(bus)
    db.commit()
    db.refresh(bus)
    return bus


@router.put("/buses/{bus_id}", response_model=BusOut)
def update_bus(bus_id: int, payload: BusCreate, db: Session = Depends(get_db), admin: Parent = Depends(require_admin)):
    bus = db.get(Bus, bus_id)
    if bus is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bus not found")
    bus.plate_no = payload.plate_no
    bus.device_id = payload.device_id
    bus.route_name = payload.route_name
    db.commit()
    db.refresh(bus)
    return bus


@router.delete("/buses/{bus_id}")
def delete_bus(bus_id: int, db: Session = Depends(get_db), admin: Parent = Depends(require_admin)):
    bus = db.get(Bus, bus_id)
    if bus is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bus not found")
    db.delete(bus)
    db.commit()
    return {"message": "Bus deleted"}


@router.post("/parent-student/link")
def link_parent_to_student(payload: ParentStudentLink, db: Session = Depends(get_db), admin: Parent = Depends(require_admin)):
    parent = db.get(Parent, payload.parent_id)
    student = db.get(Student, payload.student_id)
    if parent is None or student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parent or student not found")
    existing = db.query(ParentStudent).filter_by(parent_id=parent.id, student_id=student.id).first()
    if existing:
        return {"message": "Link already exists"}
    db.add(ParentStudent(parent_id=parent.id, student_id=student.id))
    db.commit()
    return {"message": "Parent linked to student"}


@router.post("/devices/rotate-key")
def rotate_device_key(payload: dict, db: Session = Depends(get_db), admin: Parent = Depends(require_admin)):
    bus_id = payload.get("bus_id")
    new_key = payload.get("api_key")
    if not bus_id or not new_key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="bus_id and api_key are required")
    device = db.query(Device).filter(Device.bus_id == int(bus_id)).first()
    if device is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found for bus")
    device.api_key_hash = hash_api_key(new_key)
    db.commit()
    return {"message": "Device API key rotated", "bus_id": bus_id}
