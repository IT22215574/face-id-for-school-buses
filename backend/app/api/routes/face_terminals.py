"""Driver-owned setup of boarding and exit machines for the assigned bus."""
import json
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.api.deps import get_db, require_parent
from app.api.routes.buses import assigned_driver_bus
from app.core.config import get_settings
from app.models.face_terminal import FaceTerminal
from app.models.student import Student
from app.models.student_transport import StudentTransport

router = APIRouter(prefix="/driver/machines", tags=["Face ID machines"])
Role = Literal["ENTRY", "EXIT"]


class MachineIn(BaseModel):
    model_config = {"str_strip_whitespace": True, "extra": "forbid"}
    serial: str = Field(min_length=1, max_length=40, pattern=r"^[A-Za-z0-9_-]+$")
    model: str = Field(min_length=1, max_length=100)
    timezone: str = "Asia/Colombo"
    students: dict[str, int] = Field(default_factory=dict)

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value):
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("Unknown timezone") from exc
        return value

    @field_validator("students")
    @classmethod
    def valid_pins(cls, value):
        if any(not pin or len(pin) > 32 or any(c.isspace() for c in pin) for pin in value):
            raise ValueError("Enrolled IDs must be 1–32 characters without whitespace")
        if len(set(value.values())) != len(value):
            raise ValueError("Map each student to only one enrolled ID per machine")
        return value


def machine_json(machine):
    return {"id": machine.id, "adapter_managed": machine.adapter_managed, "serial": machine.serial, "role": machine.role, "model": machine.model,
            "timezone": machine.timezone, "students": machine.students,
            "last_seen_at": machine.last_seen_at.isoformat() + "Z" if machine.last_seen_at else None}


@router.get("")
def list_machines(current_user=Depends(require_parent), db: Session = Depends(get_db)):
    bus = assigned_driver_bus(current_user, db)
    students = db.query(Student).join(StudentTransport).filter(StudentTransport.bus_id == bus.id).order_by(Student.name).all()
    return {"bus_id": bus.id, "plate_no": bus.plate_no,
            "machines": [machine_json(m) for m in db.query(FaceTerminal).filter_by(bus_id=bus.id).all()],
            "students": [{"id": s.id, "name": s.name, "grade": s.grade} for s in students]}


@router.put("/{role}")
def save_machine(role: Role, payload: MachineIn, current_user=Depends(require_parent), db: Session = Depends(get_db)):
    bus = assigned_driver_bus(current_user, db)
    allowed = {row.student_id for row in db.query(StudentTransport).filter_by(bus_id=bus.id).all()}
    if not set(payload.students.values()).issubset(allowed):
        raise HTTPException(403, "Only students assigned to your bus can be enrolled")
    if payload.serial in json.loads(get_settings().ZKTECO_DEVICES_JSON):
        raise HTTPException(409, "Serial already exists in server configuration; ask your administrator to migrate it")
    machine = db.query(FaceTerminal).filter_by(bus_id=bus.id, role=role).first()
    if machine and machine.adapter_managed:
        raise HTTPException(409, "Terminal is managed through administrator receiver integration")
    if machine and machine.serial != payload.serial:
        raise HTTPException(409, "Remove the current machine before registering a replacement")
    claimed = db.query(FaceTerminal).filter_by(serial=payload.serial).first()
    if claimed and (not machine or claimed.id != machine.id):
        raise HTTPException(409, "Machine serial is already registered")
    if machine is None:
        machine = FaceTerminal(bus_id=bus.id, role=role, **payload.model_dump())
        db.add(machine)
    else:
        # Direction and timezone are immutable once scans may have been recorded.
        if machine.timezone != payload.timezone:
            raise HTTPException(409, "Remove and re-register to change the machine timezone")
        machine.model = payload.model
        machine.students = payload.students
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Machine serial or bus slot is already registered") from exc
    return machine_json(machine)


@router.delete("/{role}")
def remove_machine(role: Role, current_user=Depends(require_parent), db: Session = Depends(get_db)):
    bus = assigned_driver_bus(current_user, db)
    machine = db.query(FaceTerminal).filter_by(bus_id=bus.id, role=role).first()
    if machine:
        if machine.adapter_managed:
            raise HTTPException(409, "Disable managed terminals through administration")
        from app.models.face_ingestion import FaceInbox, FaceEnrollment, FaceDirection
        if any(db.query(model.id).filter_by(device_id=machine.id).first() for model in (FaceInbox, FaceEnrollment, FaceDirection)):
            raise HTTPException(409, "Terminal has integration history; ask administrator to disable it")
        db.delete(machine)
        db.commit()
    return {"message": "Machine removed; recorded attendance retained"}
