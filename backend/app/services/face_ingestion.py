"""Normalize the inspected receiver's JSONL records; no device protocol commands."""
import hashlib
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from cryptography.fernet import Fernet
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import or_, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.models.face_terminal import FaceTerminal
from app.models.face_ingestion import FaceInbox, FaceEnrollment, FaceDirection, FaceNotificationJob
from app.models.event import Event, EventType
from app.models.bus_location import BusLocation
from app.models.student import Student
from app.models.parent import Parent


class ReceiverRecord(BaseModel):
    """Fields emitted by upstream _save_attlog; this is NOT a vendor wire API."""
    model_config = ConfigDict(extra='forbid')
    ts: str = Field(max_length=64)
    sn: str = Field(min_length=1, max_length=40, pattern=r'^[A-Za-z0-9_-]+$')
    pin: str = Field(min_length=1, max_length=32, pattern=r'^\S+$')
    time: str = Field(max_length=64)
    status: str = Field(max_length=32)
    verify: str = Field(max_length=32)
    raw: str = Field(min_length=1, max_length=4096)


def utc(value):
    return value.astimezone(timezone.utc).replace(tzinfo=None) if value.tzinfo else value


def ingest(db: Session, record: ReceiverRecord):
    db.execute(update(FaceTerminal).where(FaceTerminal.serial == record.sn).values(updated_at=FaceTerminal.updated_at))
    machine = db.query(FaceTerminal).filter_by(serial=record.sn).with_for_update().populate_existing().first()
    if not machine or not machine.enabled or not machine.adapter_managed:
        raise ValueError('Unknown or disabled terminal')
    # Receiver supplies no stable vendor event ID. Exact original row + serial is the identity.
    key = hashlib.sha256(f'{record.sn}\0{record.raw}'.encode()).hexdigest()
    existing = db.query(FaceInbox).filter_by(deduplication_key=key).first()
    if existing:
        db.execute(update(FaceInbox).where(FaceInbox.id == existing.id).values(duplicate_count=FaceInbox.duplicate_count + 1))
        machine.last_seen_at = datetime.utcnow()
        db.commit()
        return existing
    when = None
    error = None
    parts = record.raw.split('\t')
    if ('\n' in record.raw or '\r' in record.raw or len(parts) < 2 or parts[:2] != [record.pin, record.time]
            or (parts[2] if len(parts) > 2 else '') != record.status
            or (parts[3] if len(parts) > 3 else '') != record.verify):
        error = 'Receiver fields disagree with original row'
    try:
        local = datetime.strptime(record.time, '%Y-%m-%d %H:%M:%S')
        zone = ZoneInfo(machine.timezone)
        a, b = local.replace(tzinfo=zone, fold=0), local.replace(tzinfo=zone, fold=1)
        if a.utcoffset() != b.utcoffset() or a.astimezone(timezone.utc).astimezone(zone).replace(tzinfo=None) != local:
            raise ValueError('Ambiguous local timestamp')
        when = utc(a)
    except (ValueError, KeyError):
        error = 'Invalid or ambiguous terminal timestamp'
    row = FaceInbox(device_id=machine.id, deduplication_key=key,
        raw_payload=Fernet(get_settings().FACE_RAW_ENCRYPTION_KEY.encode()).encrypt(record.model_dump_json().encode()).decode(),
        terminal_user_id=record.pin, device_event_time=when,
        processing_status='QUARANTINED' if error else 'RECEIVED', processing_error=error)
    try:
        with db.begin_nested():
            db.add(row)
            db.flush()
    except IntegrityError:
        row = db.query(FaceInbox).filter_by(deduplication_key=key).one()
        db.execute(update(FaceInbox).where(FaceInbox.id == row.id).values(duplicate_count=FaceInbox.duplicate_count + 1))
    machine.last_seen_at = datetime.utcnow()
    db.commit()  # HTTP acceptance only after persistence
    return row


def process(db: Session, inbox_id: int):
    db.execute(update(FaceInbox).where(FaceInbox.id == inbox_id).values(duplicate_count=FaceInbox.duplicate_count))
    row = db.query(FaceInbox).filter_by(id=inbox_id).with_for_update().populate_existing().one()
    if row.event_id or row.processing_status == 'QUARANTINED':
        db.commit()
        return row
    machine = db.get(FaceTerminal, row.device_id)
    def pending(reason):
        row.processing_status = 'PENDING'
        row.processing_error = reason
        db.commit()
        return row
    if not machine.enabled:
        return pending('Terminal disabled')
    when = row.device_event_time
    settings = get_settings()
    if when is None or when > row.received_at + timedelta(seconds=settings.FACE_CLOCK_FUTURE_SECONDS):
        return pending('Clock drift: future timestamp requires investigation')
    mapping = db.query(FaceEnrollment).filter(FaceEnrollment.device_id == machine.id,
        FaceEnrollment.terminal_user_id == row.terminal_user_id, FaceEnrollment.effective_from <= when,
        or_(FaceEnrollment.effective_until.is_(None), FaceEnrollment.effective_until > when)).all()
    if len(mapping) != 1:
        return pending('Unknown or conflicting historical student mapping')
    # Registry bus assignments are immutable; retain retired serials rather than reusing them.
    direction, source = row.override_direction, 'MANUAL_OVERRIDE'
    if direction is None:
        if not machine.clock_checked_at or not machine.clock_verified_until or not (machine.clock_checked_at <= when <= machine.clock_verified_until):
            return pending('Unclassified direction: terminal clock has not been verified for scan time')
        guard = timedelta(seconds=settings.FACE_MODE_GUARD_SECONDS)
        modes = db.query(FaceDirection).filter(FaceDirection.device_id == machine.id,
            FaceDirection.effective_from <= when - guard,
            or_(FaceDirection.effective_until.is_(None), FaceDirection.effective_until > when + guard)).all()
        if len(modes) != 1:
            return pending('Unclassified direction; confirm this scan individually')
        direction, source = modes[0].event_type, 'ATTENDANT_INTERVAL'
    # Serialize same-student scans across terminals before debounce and outbox creation.
    db.execute(update(Student).where(Student.id == mapping[0].student_id).values(name=Student.name))
    debounce = timedelta(seconds=settings.FACE_SCAN_DEBOUNCE_SECONDS)
    event = db.query(Event).filter(Event.student_id == mapping[0].student_id,
        Event.bus_id == machine.bus_id, Event.source_device_id.isnot(None),
        Event.event_type == EventType(direction), Event.event_time >= when - debounce,
        Event.event_time <= when + debounce).order_by(Event.event_time).first()
    if event:
        opposite = db.query(Event.id).filter(Event.student_id == mapping[0].student_id,
            Event.bus_id == machine.bus_id, Event.event_type != EventType(direction),
            Event.event_time >= min(event.event_time, when), Event.event_time <= max(event.event_time, when)).first()
        if opposite:
            event = None
    if event and event.ingestion_key != row.deduplication_key:
        row.event_id, row.processing_status, row.processing_error = event.id, 'DUPLICATE_SCAN', None
        db.commit()
        return row
    if event is None:
        limit = timedelta(seconds=settings.FACE_GPS_MAX_AGE_SECONDS)
        # GPS timestamp is mandatory: receive time cannot locate a delayed scan reliably.
        fixes = db.query(BusLocation).filter(BusLocation.bus_id == machine.bus_id,
            BusLocation.gps_time >= when - limit, BusLocation.gps_time <= when + limit,
            BusLocation.accuracy_m.isnot(None), BusLocation.accuracy_m >= 0,
            BusLocation.accuracy_m <= settings.FACE_GPS_MAX_ACCURACY_M,
            BusLocation.lat.between(-90, 90), BusLocation.lng.between(-180, 180)).all()
        fix = min(fixes, key=lambda f: abs((utc(f.gps_time) - when).total_seconds())) if fixes else None
        historical = db.query(BusLocation.id).filter(BusLocation.bus_id == machine.bus_id,
                                                   BusLocation.gps_time.isnot(None)).first()
        event = Event(student_id=mapping[0].student_id, bus_id=machine.bus_id,
            event_type=EventType(direction), event_time=when, lat=fix.lat if fix else None,
            lng=fix.lng if fix else None, source='ZK:' + machine.serial,
            ingestion_key=row.deduplication_key, source_device_id=machine.id,
            received_at=row.received_at, direction_source=source,
            gps_accuracy_m=fix.accuracy_m if fix else None,
            gps_status='VALID' if fix else 'STALE' if historical else 'UNAVAILABLE',
            gps_timestamp=utc(fix.gps_time) if fix else None, gps_source='BUS_LOCATION' if fix else None,
            is_delayed=(row.received_at - when).total_seconds() > settings.FACE_DELAY_SECONDS)
        db.add(event)
        db.flush()
        student = db.get(Student, event.student_id)
        for link in student.student_links:
            db.add(FaceNotificationJob(event_id=event.id, parent_id=link.parent_id))
    row.event_id = event.id
    row.processing_status, row.processing_error = 'PROCESSED', None
    db.commit()  # Event + outbox + inbox transition are atomic
    return row


def deliver_job(db: Session, job_id: int):
    """Atomic claim; interrupted sends stay SENDING for manual reconciliation."""
    claimed = db.execute(update(FaceNotificationJob).where(FaceNotificationJob.id == job_id,
        FaceNotificationJob.status.in_(['PENDING', 'FAILED']),
        FaceNotificationJob.next_attempt_at <= datetime.utcnow()).values(status='SENDING', attempts=FaceNotificationJob.attempts + 1))
    db.commit()
    if not claimed.rowcount:
        return
    job = db.get(FaceNotificationJob, job_id)
    event = db.get(Event, job.event_id)
    from app.services.notification_service import send_event_notifications
    try:
        # Original UTC event date/time is used even for delayed uploads.
        success = send_event_notifications(db, db.get(Parent, job.parent_id), db.get(Student, event.student_id),
            event.event_type.value, event.id, event.bus_id, event.event_time.replace(tzinfo=timezone.utc), strict_delivery=True)
        job.status = 'SENT' if success else 'FAILED'
        job.last_error = None if success else 'Provider delivery failed; inspect notification audit'
        job.next_attempt_at = datetime.utcnow() + timedelta(seconds=min(3600, 30 * 2 ** min(job.attempts, 7)))
    except Exception:
        db.rollback()
        job = db.get(FaceNotificationJob, job_id)
        job.status, job.last_error = 'UNCERTAIN', 'Interrupted delivery: reconcile provider audit before retry'
    db.commit()


def purge_raw(db: Session):
    cutoff = datetime.utcnow() - timedelta(days=get_settings().FACE_RAW_RETENTION_DAYS)
    db.query(FaceInbox).filter(FaceInbox.received_at < cutoff).update({'raw_payload': None})
    db.commit()
