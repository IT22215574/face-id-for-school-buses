"""Legacy ZKTeco ADMS attendance push receiver (not Access Control RTLOG).

Deploy on a private device network/VPN. Legacy ADMS identifies a terminal by
serial number; that identifier is not a cryptographic credential.
"""
import json
from hashlib import sha256
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import get_settings
from app.models.bus import Bus
from app.models.device import Device
from app.models.face_terminal import FaceTerminal
from app.models.event import Event, EventType
from app.models.student import Student
from app.models.student_transport import StudentTransport

router = APIRouter(prefix="/iclock", tags=["ZKTeco ADMS"])


def terminal(request: Request, db: Session):
    serial = request.query_params.get("SN", "")
    machine = db.query(FaceTerminal).filter_by(serial=serial).first()
    if machine:
        return serial, {"bus_id": machine.bus_id, "timezone": machine.timezone,
                        "students": machine.students,
                        "fixed_event_type": "BOARDED" if machine.role == "ENTRY" else "ALIGHTED"}, machine
    config = json.loads(get_settings().ZKTECO_DEVICES_JSON).get(serial)
    if not config:
        raise HTTPException(403, "Terminal serial is not configured")
    bus_id = int(config["bus_id"])
    device = db.query(Device).filter_by(bus_id=bus_id, status="ACTIVE").first()
    if db.get(Bus, bus_id) is None or device is None:
        raise HTTPException(403, "Terminal bus or active device is not configured")
    return serial, config, device


@router.get("/cdata", response_class=PlainTextResponse)
@router.get("/cdata.aspx", response_class=PlainTextResponse, include_in_schema=False)
def options(request: Request, db: Session = Depends(get_db)):
    serial, _, device = terminal(request, db)
    device.last_seen_at = datetime.now(timezone.utc)
    db.commit()
    return (f"GET OPTION FROM: {serial}\nATTLOGStamp=0\n"
            "ErrorDelay=60\nDelay=10\nTransTimes=00:00;14:05\n"
            "TransInterval=1\nTransFlag=TransData AttLog\nRealtime=1\nEncrypt=0\n")


@router.get("/getrequest", response_class=PlainTextResponse)
@router.get("/getrequest.aspx", response_class=PlainTextResponse, include_in_schema=False)
def heartbeat(request: Request, db: Session = Depends(get_db)):
    _, _, device = terminal(request, db)
    device.last_seen_at = datetime.now(timezone.utc)
    db.commit()
    return "OK"


@router.post("/cdata", response_class=PlainTextResponse)
@router.post("/cdata.aspx", response_class=PlainTextResponse, include_in_schema=False)
async def attendance(request: Request, db: Session = Depends(get_db)):
    serial, config, device = terminal(request, db)
    if request.query_params.get("table") != "ATTLOG":
        raise HTTPException(400, "Only ATTLOG attendance uploads are supported")
    raw = bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw) > 1024 * 1024:
            raise HTTPException(413, "Attendance batch too large")
    try:
        rows = raw.decode("utf-8").strip().splitlines()
        parsed = []
        for row in rows:
            fields = row.strip().split("\t")
            if len(fields) < 4:
                raise ValueError("Expected tab-separated PIN, time, status, verification")
            pin = fields[0].removeprefix("PIN=")
            student_id = config.get("students", {}).get(pin)
            if student_id is None:
                raise ValueError(f"Unmapped enrolled user ID: {pin}")
            assignment = db.get(StudentTransport, int(student_id))
            if not assignment or assignment.bus_id != device.bus_id or db.get(Student, int(student_id)) is None:
                raise ValueError(f"User {pin} is not assigned to this bus")
            mapping = config.get("status_map", {"0": "BOARDED", "1": "ALIGHTED"})
            event_type = EventType(config["fixed_event_type"] if "fixed_event_type" in config else mapping[fields[2]])
            when = datetime.strptime(fields[1], "%Y-%m-%d %H:%M:%S").replace(
                tzinfo=ZoneInfo(config.get("timezone", "Asia/Colombo"))).astimezone(timezone.utc)
            parsed.append((int(student_id), event_type, when))
    except (ValueError, KeyError, UnicodeError) as exc:
        raise HTTPException(422, str(exc)) from exc
    # Validate the entire batch before writing. Replayed batches do not duplicate events.
    source = f"ZK:{serial}"
    if len(source) > 50:
        raise HTTPException(422, "Terminal serial is too long")
    for student_id, event_type, when in parsed:
        key = sha256(f"{serial}|{device.bus_id}|{student_id}|{event_type.value}|{when.isoformat()}".encode()).hexdigest()
        existing = db.query(Event).filter_by(ingestion_key=key).first()
        if existing is None:
            db.add(Event(student_id=student_id, bus_id=device.bus_id, event_type=event_type,
                event_time=when.replace(tzinfo=None), lat=None, lng=None, source=source, ingestion_key=key))
            db.flush()
    device.last_seen_at = datetime.now(timezone.utc)
    db.commit()
    return f"OK: {len(parsed)}"
