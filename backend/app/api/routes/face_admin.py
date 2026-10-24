"""Administrative operations and private receiver-to-backend boundary."""
import hmac
from datetime import datetime, timedelta
from typing import Literal
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field, AwareDatetime
from sqlalchemy import or_, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.api.deps import get_db, require_admin, require_parent
from app.api.routes.buses import assigned_driver_bus
from app.api.routes.face_terminals import MachineIn
from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.models import Bus, Student, AuditLog, Event
from app.models.student_transport import StudentTransport
from app.models.face_terminal import FaceTerminal
from app.models.face_ingestion import FaceEnrollment, FaceDirection, FaceInbox, FaceNotificationJob
from app.services.face_ingestion import ReceiverRecord, ingest, process, utc

router = APIRouter(tags=['Face recognition integration'])
Direction = Literal['BOARDED', 'ALIGHTED']


def audit(db, actor, action, entity_id):
    db.add(AuditLog(user_id=actor.id, action=action, entity='FACE_TERMINAL', entity_id=entity_id))


def machine_or_404(db, device_id):
    db.execute(update(FaceTerminal).where(FaceTerminal.id == device_id).values(updated_at=FaceTerminal.updated_at))
    machine = db.query(FaceTerminal).filter_by(id=device_id).with_for_update().first()
    if not machine:
        raise HTTPException(404, 'Terminal not found')
    return machine


def device_json(machine):
    seen = utc(machine.last_seen_at) if machine.last_seen_at else None
    return {'id': machine.id, 'serial': machine.serial, 'device_name': machine.device_name,
        'model': machine.model, 'firmware_version': machine.firmware_version, 'bus_id': machine.bus_id,
        'timezone': machine.timezone, 'enabled': machine.enabled, 'adapter_managed': machine.adapter_managed,
        'last_seen_at': seen.isoformat() + 'Z' if seen else None,
        'connection_status': 'DISABLED' if not machine.enabled else 'ONLINE' if seen and seen > datetime.utcnow() - timedelta(minutes=5) else 'OFFLINE',
        'clock_verified_until': machine.clock_verified_until.isoformat() + 'Z' if machine.clock_verified_until else None,
        'configuration_status': 'HARDWARE_UNVERIFIED'}


class Register(MachineIn):
    bus_id: int
    role: Literal['ENTRY', 'EXIT'] = 'ENTRY'
    device_name: str = Field(min_length=1, max_length=100)
    firmware_version: str | None = Field(default=None, max_length=100)


class Metadata(BaseModel):
    device_name: str = Field(min_length=1, max_length=100)
    firmware_version: str | None = Field(default=None, max_length=100)
    enabled: bool


@router.get('/admin/face-devices')
def devices(actor=Depends(require_admin), db: Session = Depends(get_db)):
    return [device_json(m) for m in db.query(FaceTerminal).order_by(FaceTerminal.id).all()]


@router.post('/admin/face-devices', status_code=201)
def register(payload: Register, actor=Depends(require_admin), db: Session = Depends(get_db)):
    if not db.get(Bus, payload.bus_id):
        raise HTTPException(404, 'Bus not found')
    if payload.students:
        raise HTTPException(422, 'Create confirmed enrollment mappings separately')
    import json
    if payload.serial in json.loads(get_settings().ZKTECO_DEVICES_JSON):
        raise HTTPException(409, 'Serial already belongs to legacy configuration')
    machine = FaceTerminal(**payload.model_dump(), adapter_managed=True)
    db.add(machine)
    try:
        db.flush()
        audit(db, actor, 'FACE_REGISTER', machine.id)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Serial or bus door slot already registered; retain historical serials')
    return device_json(machine)


@router.patch('/admin/face-devices/{device_id}')
def metadata(device_id: int, payload: Metadata, actor=Depends(require_admin), db: Session = Depends(get_db)):
    machine = machine_or_404(db, device_id)
    if machine.enabled != payload.enabled or machine.firmware_version != payload.firmware_version:
        machine.clock_checked_at = machine.clock_verified_until = None
    for key, value in payload.model_dump().items():
        setattr(machine, key, value)
    audit(db, actor, 'FACE_METADATA_OR_REVOCATION', device_id)
    db.commit()
    return device_json(machine)


@router.post('/admin/face-devices/{device_id}/adopt')
def adopt(device_id: int, actor=Depends(require_admin), db: Session = Depends(get_db)):
    machine = machine_or_404(db, device_id)
    machine.adapter_managed = True
    machine.clock_checked_at = machine.clock_verified_until = None
    audit(db, actor, 'FACE_ADOPT_RECEIVER_ADAPTER', device_id)
    db.commit()
    return device_json(machine)


class Enrollment(BaseModel):
    terminal_user_id: str = Field(min_length=1, max_length=32, pattern=r'^\S+$')
    student_id: int
    effective_from: AwareDatetime
    effective_until: AwareDatetime | None = None
    consent_reference: str = Field(min_length=1, max_length=200)
    manual_enrollment_confirmed: Literal[True]


@router.get('/admin/face-devices/{device_id}/enrollments')
def enrollments(device_id: int, actor=Depends(require_admin), db: Session = Depends(get_db)):
    machine_or_404(db, device_id)
    rows = db.query(FaceEnrollment).filter_by(device_id=device_id).order_by(FaceEnrollment.effective_from.desc()).all()
    return [{'id': r.id, 'terminal_user_id': r.terminal_user_id, 'student_id': r.student_id,
        'student_name': db.get(Student, r.student_id).name,
        'effective_from': r.effective_from.isoformat() + 'Z',
        'effective_until': r.effective_until.isoformat() + 'Z' if r.effective_until else None,
        'enrollment_status': 'ENDED' if r.effective_until and r.effective_until <= datetime.utcnow() else 'CONFIRMED'} for r in rows]


@router.post('/admin/face-devices/{device_id}/enrollments')
def enroll(device_id: int, payload: Enrollment, actor=Depends(require_admin), db: Session = Depends(get_db)):
    machine = machine_or_404(db, device_id)  # serialize conflicting mappings on PostgreSQL
    assignment = db.get(StudentTransport, payload.student_id)
    if not assignment or assignment.bus_id != machine.bus_id:
        raise HTTPException(403, 'Student must be assigned to terminal bus')
    start, end = utc(payload.effective_from), utc(payload.effective_until) if payload.effective_until else None
    if end and end <= start:
        raise HTTPException(422, 'Invalid enrollment interval')
    overlaps = db.query(FaceEnrollment).filter(FaceEnrollment.device_id == device_id,
        or_(FaceEnrollment.terminal_user_id == payload.terminal_user_id, FaceEnrollment.student_id == payload.student_id),
        or_(FaceEnrollment.effective_until.is_(None), FaceEnrollment.effective_until > start))
    if end:
        overlaps = overlaps.filter(FaceEnrollment.effective_from < end)
    if overlaps.first():
        raise HTTPException(409, 'Conflicting enrollment interval')
    row = FaceEnrollment(device_id=device_id, terminal_user_id=payload.terminal_user_id,
        student_id=payload.student_id, effective_from=start, effective_until=end, consent_reference=payload.consent_reference)
    db.add(row)
    audit(db, actor, 'FACE_ENROLLMENT_CONFIRMED', device_id)
    db.commit()
    return {'id': row.id}


@router.delete('/admin/face-devices/{device_id}/enrollments/{mapping_id}')
def end_enrollment(device_id: int, mapping_id: int, actor=Depends(require_admin), db: Session = Depends(get_db)):
    machine_or_404(db, device_id)
    row = db.query(FaceEnrollment).filter_by(id=mapping_id, device_id=device_id).first()
    if not row:
        raise HTTPException(404, 'Mapping not found')
    now = datetime.utcnow()
    if row.effective_from > now:
        raise HTTPException(409, 'Future enrollment requires administrator correction')
    if not row.effective_until or row.effective_until > now:
        row.effective_until = now
    audit(db, actor, 'FACE_ENROLLMENT_ENDED_DELETE_ON_TERMINAL_REQUIRED', device_id)
    db.commit()
    return {'message': 'Mapping ended. Delete biometric enrollment on the physical terminal and record completion in your consent register.'}


class ClockCheck(BaseModel):
    valid_until: AwareDatetime
    observed_error_seconds: float = Field(ge=0, allow_inf_nan=False)
    evidence: str = Field(min_length=5, max_length=200)


@router.post('/admin/face-devices/{device_id}/clock-check')
def clock_check(device_id: int, payload: ClockCheck, actor=Depends(require_admin), db: Session = Depends(get_db)):
    machine = machine_or_404(db, device_id)
    now, until = datetime.utcnow(), utc(payload.valid_until)
    if not now < until <= now + timedelta(hours=24):
        raise HTTPException(422, 'Clock verification must expire within 24 hours')
    if payload.observed_error_seconds >= get_settings().FACE_MODE_GUARD_SECONDS:
        raise HTTPException(422, 'Terminal clock error exceeds direction boundary guard')
    machine.clock_checked_at, machine.clock_verified_until = now, until
    db.add(AuditLog(user_id=actor.id, action='FACE_CLOCK_CHECK', entity='FACE_TERMINAL', entity_id=device_id,
        after_json=payload.model_dump_json()))
    db.commit()
    return device_json(machine)


class Mode(BaseModel):
    event_type: Direction


@router.post('/face-devices/{device_id}/direction')
def set_mode(device_id: int, payload: Mode, actor=Depends(require_parent), db: Session = Depends(get_db)):
    machine = machine_or_404(db, device_id)
    if actor.role != 'ADMIN' and assigned_driver_bus(actor, db).id != machine.bus_id:
        raise HTTPException(403, 'Terminal belongs to another bus')
    if not machine.enabled:
        raise HTTPException(409, 'Terminal disabled')
    now = datetime.utcnow()
    for mode in db.query(FaceDirection).filter_by(device_id=device_id, effective_until=None).all():
        mode.effective_until = now
    db.add(FaceDirection(device_id=device_id, event_type=payload.event_type, effective_from=now, actor_id=actor.id))
    audit(db, actor, 'FACE_DIRECTION_' + payload.event_type, device_id)
    db.commit()
    return {'effective_from': now.isoformat() + 'Z', 'event_type': payload.event_type,
        'message': 'Clock uncertainty near mode changes requires supervised classification'}


@router.get('/admin/face-events')
def events(device_id: int | None = None, status: str | None = None,
           limit: int = Query(100, ge=1, le=500), actor=Depends(require_admin), db: Session = Depends(get_db)):
    query = db.query(FaceInbox)
    if device_id is not None:
        query = query.filter_by(device_id=device_id)
    if status:
        query = query.filter_by(processing_status=status)
    result = []
    for r in query.order_by(FaceInbox.id.desc()).limit(limit).all():
        event = db.get(Event, r.event_id) if r.event_id else None
        machine = db.get(FaceTerminal, r.device_id)
        result.append({'id': r.id, 'device_id': r.device_id, 'serial': machine.serial, 'bus_id': machine.bus_id,
            'terminal_user_id': r.terminal_user_id, 'device_event_time': r.device_event_time.isoformat() + 'Z' if r.device_event_time else None,
            'received_at': r.received_at.isoformat() + 'Z', 'processing_status': r.processing_status,
            'processing_error': r.processing_error, 'duplicate_count': r.duplicate_count, 'event_id': r.event_id,
            'student_id': event.student_id if event else None,
            'student_name': db.get(Student, event.student_id).name if event else None,
            'event_type': event.event_type.value if event else None,
            'gps_timestamp': event.gps_timestamp.isoformat() + 'Z' if event and event.gps_timestamp else None,
            'gps_accuracy_m': event.gps_accuracy_m if event else None,
            'direction_source': event.direction_source if event else None,
            'gps_status': event.gps_status if event else None, 'is_delayed': event.is_delayed if event else None,
            'source': event.source if event else 'RECEIVER_JSONL',
            'notifications': [{'id': j.id, 'status': j.status, 'attempts': j.attempts, 'last_error': j.last_error} for j in db.query(FaceNotificationJob).filter_by(event_id=r.event_id).all()] if event else []})
    return result


class Classification(BaseModel):
    event_type: Direction
    reason: str = Field(min_length=5, max_length=200)


@router.post('/admin/face-events/{inbox_id}/classify')
def classify(inbox_id: int, payload: Classification, actor=Depends(require_admin), db: Session = Depends(get_db)):
    row = db.query(FaceInbox).filter_by(id=inbox_id).with_for_update().first()
    if not row:
        raise HTTPException(404, 'Record not found')
    if row.event_id or row.processing_status == 'QUARANTINED':
        raise HTTPException(409, 'Processed or invalid record cannot be reclassified')
    row.override_direction, row.override_actor_id, row.override_reason = payload.event_type, actor.id, payload.reason
    audit(db, actor, 'FACE_SUPERVISED_CLASSIFICATION', row.device_id)
    db.commit()
    return {'status': process(db, row.id).processing_status}


@router.post('/admin/face-events/{inbox_id}/reprocess')
def reprocess(inbox_id: int, actor=Depends(require_admin), db: Session = Depends(get_db)):
    row = db.get(FaceInbox, inbox_id)
    if not row:
        raise HTTPException(404, 'Record not found')
    audit(db, actor, 'FACE_REPROCESS', row.device_id)
    db.commit()
    return {'status': process(db, inbox_id).processing_status}


class Reconciliation(BaseModel):
    resolution: Literal['DELIVERED', 'RETRY']
    evidence: str = Field(min_length=5, max_length=200)


@router.post('/admin/face-notifications/{job_id}/reconcile')
def reconcile(job_id: int, payload: Reconciliation, actor=Depends(require_admin), db: Session = Depends(get_db)):
    db.execute(update(FaceNotificationJob).where(FaceNotificationJob.id == job_id).values(status=FaceNotificationJob.status))
    job = db.query(FaceNotificationJob).filter_by(id=job_id).with_for_update().populate_existing().first()
    if not job:
        raise HTTPException(404, 'Notification job not found')
    if job.status not in {'SENDING', 'UNCERTAIN', 'FAILED'}:
        raise HTTPException(409, 'Only failed or ambiguous jobs can be reconciled')
    # A SENDING job may still be actively sending. Require the worker to be stopped and
    # the provider audit reviewed; record this operational evidence explicitly.
    db.add(AuditLog(user_id=actor.id, action='FACE_NOTIFICATION_RECONCILE', entity='FACE_NOTIFICATION_JOB',
        entity_id=job.id, before_json=job.status, after_json=payload.model_dump_json()))
    job.status = 'SENT' if payload.resolution == 'DELIVERED' else 'PENDING'
    job.last_error = None
    if payload.resolution == 'RETRY':
        job.attempts, job.next_attempt_at = 0, datetime.utcnow()
    db.commit()
    return {'status': job.status}


@router.post('/internal/face-receiver/records', status_code=202)
@limiter.limit('300/minute')
def receiver_record(request: Request, payload: ReceiverRecord,
                    token: str = Header('', alias='x-face-adapter-token'), db: Session = Depends(get_db)):
    expected = get_settings().FACE_ADAPTER_TOKEN
    if not expected or not hmac.compare_digest(expected, token):
        raise HTTPException(401, 'Invalid adapter credentials')
    from cryptography.fernet import Fernet
    try:
        Fernet(get_settings().FACE_RAW_ENCRYPTION_KEY.encode())
    except ValueError as exc:
        raise HTTPException(503, 'Raw attendance encryption is not configured') from exc
    try:
        row = ingest(db, payload)
    except ValueError as exc:
        raise HTTPException(403, str(exc)) from exc
    return {'inbox_id': row.id, 'status': row.processing_status}
