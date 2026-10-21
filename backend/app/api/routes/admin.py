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
from app.schemas.driver_registration import DriverRegistrationCreate, DriverRegistrationUpdate

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
    from sqlalchemy.exc import IntegrityError
    db.add(bus)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Bus plate or device identifier is already registered') from None
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
    from sqlalchemy.exc import IntegrityError
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Bus plate or device identifier is already registered') from None
    db.refresh(bus)
    return bus


@router.delete("/buses/{bus_id}")
def delete_bus(bus_id: int, db: Session = Depends(get_db), admin: Parent = Depends(require_admin)):
    bus = db.get(Bus, bus_id)
    if bus is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bus not found")
    reject_references(db, Bus.__table__, bus.id)
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


@router.put("/students/{student_id}/bus/{bus_id}")
def assign_student_bus(student_id: int, bus_id: int, db: Session = Depends(get_db), admin: Parent = Depends(require_admin)):
    from app.models.student_transport import StudentTransport
    if db.get(Student, student_id) is None or db.get(Bus, bus_id) is None:
        raise HTTPException(status_code=404, detail="Student or bus not found")
    assignment = db.get(StudentTransport, student_id)
    if assignment:
        assignment.bus_id = bus_id
    else:
        db.add(StudentTransport(student_id=student_id, bus_id=bus_id))
    db.commit()
    return {"student_id": student_id, "bus_id": bus_id}


@router.get('/driver-registrations')
def list_driver_registrations(db: Session = Depends(get_db), admin: Parent = Depends(require_admin)):
    from app.models.payroll import Driver
    return [dict(id=d.id, name=d.name, phone=d.phone, email=d.user.email,
                 bus_id=d.bus_id, plate_no=d.bus.plate_no if d.bus else None,
                 route_name=d.bus.route_name if d.bus else None, status=d.status)
            for d in db.query(Driver).order_by(Driver.created_at.desc()).all()]


@router.post('/driver-registrations', status_code=201)
def register_driver(payload: DriverRegistrationCreate, db: Session = Depends(get_db), admin: Parent = Depends(require_admin)):
    from sqlalchemy import func
    from sqlalchemy.exc import IntegrityError
    from app.models.payroll import Driver
    from app.models.driver_registration import DriverRegistration
    from app.core.encryption import encrypt_text
    if db.get(Bus, payload.bus_id) is None:
        raise HTTPException(404, 'Select an existing bus and route')
    if db.query(Parent).filter((func.lower(Parent.email) == payload.email) | (Parent.phone == payload.phone)).first():
        raise HTTPException(409, 'Email or phone is already registered')
    if db.query(Driver).filter(Driver.nic == payload.nic).first():
        raise HTTPException(409, 'Driver ID is already registered')
    if db.query(Driver).filter_by(bus_id=payload.bus_id, status='ACTIVE').first():
        raise HTTPException(409, 'This bus already has an active driver')
    if payload.assistant and (payload.assistant.nic == payload.nic or payload.assistant.phone == payload.phone or payload.assistant.email == payload.email):
        raise HTTPException(422, 'Assistant must have separate ID and contact details')
    details = payload.model_dump_json(exclude={'password', 'license_no', 'bus_id', 'name', 'phone', 'email', 'nic'})
    encrypted = encrypt_text(details)
    try:
        user = Parent(name=payload.name, phone=payload.phone, email=payload.email,
                      password_hash=hash_password(payload.password), role='DRIVER')
        db.add(user)
        db.flush()
        driver = Driver(user_id=user.id, name=payload.name, phone=payload.phone,
                        nic=payload.nic, license_no='', bus_id=payload.bus_id, status='ACTIVE')
        db.add(driver)
        db.flush()
        db.add(DriverRegistration(driver_id=driver.id, encrypted_details=encrypted))
        db.commit()
        return {'id': driver.id, 'message': 'Driver account created and assigned to bus'}
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Account or driver details are already registered') from None


@router.get('/driver-registrations/{driver_id}')
def driver_registration_details(driver_id: int, db: Session = Depends(get_db), admin: Parent = Depends(require_admin)):
    import json
    from app.core.encryption import decrypt_text
    from app.models.driver_registration import DriverRegistration
    from app.models.payroll import Driver
    driver = db.get(Driver, driver_id)
    if driver is None:
        raise HTTPException(404, 'Driver not found')
    registration = db.get(DriverRegistration, driver_id)
    return dict(id=driver.id, bus_id=driver.bus_id, name=driver.name, phone=driver.phone, email=driver.user.email,
                nic=driver.nic, license_no=driver.license_no,
                **(json.loads(decrypt_text(registration.encrypted_details)) if registration else {}))


def reject_references(db, table, record_id, allowed=()):
    """Prevent deleting records with linked operational or financial data."""
    from sqlalchemy import select
    for child in table.metadata.sorted_tables:
        if child.name in allowed:
            continue
        for column in child.columns:
            if any(fk.column.table is table for fk in column.foreign_keys):
                if db.execute(select(column).where(column == record_id).limit(1)).first():
                    raise HTTPException(409, f'Remove or reassign linked {child.name.replace("_", " ")} before deleting')


@router.put('/driver-registrations/{driver_id}')
def update_driver_registration(driver_id: int, payload: DriverRegistrationUpdate, db: Session = Depends(get_db), admin: Parent = Depends(require_admin)):
    from sqlalchemy import func
    from sqlalchemy.exc import IntegrityError
    from app.models.payroll import Driver
    from app.models.driver_registration import DriverRegistration
    from app.core.encryption import encrypt_text
    driver = db.get(Driver, driver_id)
    if driver is None:
        raise HTTPException(404, 'Driver not found')
    if db.get(Bus, payload.bus_id) is None:
        raise HTTPException(404, 'Select an existing bus and route')
    if db.query(Parent).filter(Parent.id != driver.user_id, (func.lower(Parent.email) == payload.email) | (Parent.phone == payload.phone)).first():
        raise HTTPException(409, 'Email or phone is already registered')
    if db.query(Driver).filter(Driver.id != driver_id, Driver.nic == payload.nic).first():
        raise HTTPException(409, 'Driver ID is already registered')
    if db.query(Driver).filter(Driver.id != driver_id, Driver.bus_id == payload.bus_id, Driver.status == 'ACTIVE').first():
        raise HTTPException(409, 'This bus already has an active driver')
    if payload.assistant and (payload.assistant.nic == payload.nic or payload.assistant.phone == payload.phone or payload.assistant.email == payload.email):
        raise HTTPException(422, 'Assistant must have separate ID and contact details')
    try:
        for key in ('name', 'phone', 'nic', 'bus_id'):
            setattr(driver, key, getattr(payload, key))
        for key in ('name', 'phone', 'email'):
            setattr(driver.user, key, getattr(payload, key))
        if payload.password is not None:
            driver.user.password_hash = hash_password(payload.password)
            for token in driver.user.refresh_tokens:
                token.revoked = True
        encrypted = encrypt_text(payload.model_dump_json(exclude={'password', 'bus_id', 'name', 'phone', 'email', 'nic'}))
        registration = db.get(DriverRegistration, driver_id)
        if registration:
            registration.encrypted_details = encrypted
        else:
            db.add(DriverRegistration(driver_id=driver_id, encrypted_details=encrypted))
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Account or driver details are already registered') from None
    return {'id': driver.id, 'message': 'Driver updated'}


@router.delete('/driver-registrations/{driver_id}')
def delete_driver_registration(driver_id: int, db: Session = Depends(get_db), admin: Parent = Depends(require_admin)):
    from app.models.payroll import Driver
    from app.models.driver_registration import DriverRegistration
    driver = db.get(Driver, driver_id)
    if driver is None:
        raise HTTPException(404, 'Driver not found')
    reject_references(db, Driver.__table__, driver_id, ('driver_registrations',))
    user = driver.user
    reject_references(db, Parent.__table__, user.id, ('drivers', 'refresh_tokens', 'notifications'))
    registration = db.get(DriverRegistration, driver_id)
    if registration:
        db.delete(registration)
        db.flush()
    db.delete(driver)
    db.flush()
    db.delete(user)
    db.commit()
    return {'message': 'Driver and login deleted'}
