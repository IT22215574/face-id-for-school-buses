"""SYNTHETIC receiver-format fixtures. No hardware compatibility assertions."""
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event as sa_event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app.api.deps import get_db, require_admin, require_parent
from app.api.routes.face_admin import router
from app.core.config import get_settings
from app.db.base import Base
from app.models import Bus, Student, Parent, ParentStudent, Event
from app.models.face_terminal import FaceTerminal
from app.models.student_transport import StudentTransport
from app.models.bus_location import BusLocation
from app.models.face_ingestion import FaceInbox, FaceEnrollment, FaceDirection, FaceNotificationJob
from app.services.face_ingestion import ReceiverRecord, ingest, process, deliver_job, purge_raw


NOW = datetime(2026, 10, 20, 2, 0)


def record(pin='1001', when='2026-10-20 07:30:00', serial='SYNTHETIC-1'):
    return ReceiverRecord(ts='2026-10-20T02:00:00Z', sn=serial, pin=pin, time=when,
                          status='0', verify='15', raw=f'{pin}\t{when}\t0\t15\t0')


@pytest.fixture
def setup(monkeypatch):
    from cryptography.fernet import Fernet
    monkeypatch.setattr(get_settings(), "FACE_RAW_ENCRYPTION_KEY", Fernet.generate_key().decode())
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        bus = Bus(plate_no='SYNTHETIC', device_id='synthetic-bus', route_name='Test')
        student = Student(name='Synthetic student', grade='5', school_id='Test')
        parent = Parent(name='Test admin', email='synthetic@test.invalid', phone='1', role='ADMIN', password_hash='x')
        db.add_all([bus, student, parent]); db.flush()
        machine = FaceTerminal(bus_id=bus.id, serial='SYNTHETIC-1', model='UNVERIFIED', role='ENTRY', adapter_managed=True, students={}, clock_checked_at=NOW - timedelta(days=1), clock_verified_until=NOW + timedelta(days=1))
        db.add_all([machine, ParentStudent(student_id=student.id, parent_id=parent.id),
                    StudentTransport(student_id=student.id, bus_id=bus.id)])
        db.flush()
        db.add(FaceEnrollment(device_id=machine.id, student_id=student.id, terminal_user_id='1001',
                              effective_from=NOW - timedelta(days=1), consent_reference='synthetic-consent'))
        db.add(FaceDirection(device_id=machine.id, event_type='BOARDED', effective_from=NOW - timedelta(hours=1), actor_id=parent.id))
        db.commit()
        app = FastAPI(); app.include_router(router)
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[require_admin] = lambda: parent
        app.dependency_overrides[require_parent] = lambda: parent
        with TestClient(app) as client:
            yield db, machine, student, parent, client
    engine.dispose()


def test_historical_gps_delayed_event_and_outbox_atomic(setup):
    db, machine, student, _, _ = setup
    db.add_all([BusLocation(bus_id=machine.bus_id, lat=6, lng=80, gps_time=NOW, accuracy_m=10),
                BusLocation(bus_id=machine.bus_id, lat=9, lng=81, gps_time=datetime.utcnow(), accuracy_m=5)])
    db.commit()
    row = process(db, ingest(db, record()).id)
    event = db.get(Event, row.event_id)
    assert event.lat == 6 and event.gps_status == 'VALID'
    assert event.gps_accuracy_m == 10 and event.gps_timestamp == NOW
    assert event.event_time == NOW and event.is_delayed
    assert event.student_id == student.id
    assert db.query(FaceNotificationJob).count() == 1
    assert process(db, row.id).event_id == event.id
    assert db.query(FaceNotificationJob).count() == 1


def test_replay_and_duplicate_scans(setup):
    db, *_ = setup
    row = process(db, ingest(db, record()).id)
    assert ingest(db, record()).id == row.id
    assert db.get(FaceInbox, row.id).duplicate_count == 1
    repeated = process(db, ingest(db, record(when='2026-10-20 07:30:04')).id)
    assert repeated.processing_status == 'DUPLICATE_SCAN'
    assert db.query(Event).count() == db.query(FaceNotificationJob).count() == 1


@pytest.mark.parametrize('pin,when,expected', [('unknown', '2026-10-20 07:30:00', 'PENDING'),
    ('1001', 'bad', 'QUARANTINED'), ('1001', '2099-01-01 00:00:00', 'PENDING')])
def test_invalid_unknown_and_clock_drift(setup, pin, when, expected):
    db, *_ = setup
    row = process(db, ingest(db, record(pin=pin, when=when)).id)
    assert row.processing_status == expected
    assert db.query(Event).count() == db.query(FaceNotificationJob).count() == 0
    assert row.raw_payload and '1001' not in row.raw_payload


def test_mode_is_historical_and_boundary_requires_classification(setup):
    db, machine, _, parent, client = setup
    old = db.query(FaceDirection).one(); old.effective_until = NOW + timedelta(minutes=10)
    db.add(FaceDirection(device_id=machine.id, event_type='ALIGHTED', effective_from=old.effective_until, actor_id=parent.id))
    db.commit()
    late = process(db, ingest(db, record(when='2026-10-20 07:45:00')).id)
    earlier = process(db, ingest(db, record()).id)
    assert db.get(Event, late.event_id).event_type.value == 'ALIGHTED'
    assert db.get(Event, earlier.event_id).event_type.value == 'BOARDED'
    boundary = process(db, ingest(db, record(when='2026-10-20 07:40:00')).id)
    assert boundary.processing_status == 'PENDING'
    assert client.post(f'/admin/face-events/{boundary.id}/classify', json={'event_type': 'WRONG', 'reason': 'test evidence'}).status_code == 422
    assert client.post(f'/admin/face-events/{boundary.id}/classify', json={'event_type': 'ALIGHTED', 'reason': 'supervised synthetic test'}).status_code == 200
    assert db.get(Event, boundary.event_id).direction_source == 'MANUAL_OVERRIDE'


@pytest.mark.parametrize('age,accuracy,status', [(None, None, 'UNAVAILABLE'), (500, 5, 'STALE'), (0, None, 'STALE'), (0, 500, 'STALE')])
def test_missing_stale_and_unqualified_gps(setup, age, accuracy, status):
    db, machine, *_ = setup
    if age is not None:
        db.add(BusLocation(bus_id=machine.bus_id, lat=6, lng=80, gps_time=NOW + timedelta(seconds=age), accuracy_m=accuracy)); db.commit()
    row = process(db, ingest(db, record()).id)
    event = db.get(Event, row.event_id)
    assert event.gps_status == status and event.lat is None


def test_mapping_history_not_current_json(setup):
    db, machine, student, _, client = setup
    machine.students = {'1001': 999}
    db.query(FaceEnrollment).one().effective_until = NOW - timedelta(seconds=1)
    db.commit()
    row = process(db, ingest(db, record()).id)
    assert row.processing_status == 'PENDING'
    # Re-enrollment starts at the confirmed actual time, without altering old mapping.
    payload = {'terminal_user_id': '1001', 'student_id': student.id, 'effective_from': NOW.replace(tzinfo=timezone.utc).isoformat(),
               'consent_reference': 'synthetic', 'manual_enrollment_confirmed': True}
    assert client.post(f'/admin/face-devices/{machine.id}/enrollments', json=payload).status_code == 200
    assert client.post(f'/admin/face-devices/{machine.id}/enrollments', json=payload).status_code == 409
    assert process(db, row.id).processing_status == 'PROCESSED'


def test_registration_secret_auth_and_revocation(setup, monkeypatch):
    db, machine, _, _, client = setup
    monkeypatch.setattr(get_settings(), 'FACE_ADAPTER_TOKEN', 'synthetic-secret')
    path = '/internal/face-receiver/records'
    assert client.post(path, json=record().model_dump()).status_code == 401
    assert client.post(path, json=record().model_dump(), headers={'x-api-key': 'synthetic-secret'}).status_code == 401
    assert client.post(path, json=record().model_dump(), headers={'x-face-adapter-token': 'synthetic-secret'}).status_code == 202
    payload = {'bus_id': machine.bus_id, 'role': 'EXIT', 'serial': 'SYNTHETIC-2', 'model': 'Unverified', 'device_name': 'Test'}
    assert client.post('/admin/face-devices', json=payload).status_code == 201
    assert client.post('/admin/face-devices', json=payload).status_code == 409
    assert client.post('/admin/face-devices', json=payload | {'bus_id': 999, 'serial': 'MISSING'}).status_code == 404
    assert client.patch(f'/admin/face-devices/{machine.id}', json={'device_name': 'Test', 'enabled': False}).status_code == 200
    assert client.post(path, json=record().model_dump(), headers={'x-face-adapter-token': 'synthetic-secret'}).status_code == 403
    assert process(db, db.query(FaceInbox).one().id).processing_status == 'PENDING'
    assert 'raw_payload' not in client.get('/admin/face-events').text


def test_notification_retry_and_original_time(setup, monkeypatch):
    db, *_ = setup
    process(db, ingest(db, record()).id)
    job = db.query(FaceNotificationJob).one()
    calls = []
    def send(*args, **kwargs):
        calls.append(args[-1]); return len(calls) > 1
    monkeypatch.setattr('app.services.notification_service.send_event_notifications', send)
    deliver_job(db, job.id)
    assert job.status == 'FAILED'
    deliver_job(db, job.id)
    assert len(calls) == 1  # backoff
    job.next_attempt_at = datetime.utcnow() - timedelta(seconds=1); db.commit()
    deliver_job(db, job.id); deliver_job(db, job.id)
    assert job.status == 'SENT' and len(calls) == 2
    assert calls[0] == NOW.replace(tzinfo=timezone.utc)


def test_database_failure_does_not_commit_partial_attendance(setup):
    db, *_ = setup
    row_id = ingest(db, record()).id
    def fail(session, flush_context, instances):
        if any(isinstance(obj, FaceNotificationJob) for obj in session.new):
            raise RuntimeError('Synthetic storage failure')
    sa_event.listen(db, 'before_flush', fail)
    with pytest.raises(RuntimeError): process(db, row_id)
    db.rollback(); sa_event.remove(db, 'before_flush', fail)
    assert db.query(Event).count() == db.query(FaceNotificationJob).count() == 0
    assert db.get(FaceInbox, row_id).processing_status == 'RECEIVED'
    assert process(db, row_id).processing_status == 'PROCESSED'


def test_retention_keeps_dedup_identity(setup):
    db, *_ = setup
    row = ingest(db, record()); row.received_at = datetime.utcnow() - timedelta(days=60); db.commit()
    purge_raw(db); db.refresh(row)
    assert row.raw_payload is None
    assert ingest(db, record()).id == row.id


def test_concurrent_replay_file_database(tmp_path, monkeypatch):
    from cryptography.fernet import Fernet
    monkeypatch.setattr(get_settings(), "FACE_RAW_ENCRYPTION_KEY", Fernet.generate_key().decode())
    engine = create_engine(f'sqlite:///{tmp_path}/concurrent.db', connect_args={'timeout': 20})
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        bus = Bus(plate_no='TEST', device_id='test', route_name='Test'); db.add(bus); db.flush()
        db.add(FaceTerminal(bus_id=bus.id, serial='SYNTHETIC-1', model='test', role='ENTRY', students={}, adapter_managed=True)); db.commit()
    def upload(_):
        with Session(engine) as db:
            return ingest(db, record()).id
    with ThreadPoolExecutor(max_workers=4) as pool:
        ids = list(pool.map(upload, range(8)))
    assert len(set(ids)) == 1
    with Session(engine) as db:
        assert db.query(FaceInbox).count() == 1
    engine.dispose()


def test_admin_rbac_and_driver_direction_isolation(setup):
    from app.core.security import get_current_parent
    from app.models.payroll import Driver
    db, machine, _, parent, client = setup
    client.app.dependency_overrides.pop(require_admin)
    client.app.dependency_overrides[get_current_parent] = lambda: parent
    parent.role = 'PARENT'; db.commit()
    assert client.get('/admin/face-devices').status_code == 403
    assert client.post(f'/face-devices/{machine.id}/direction', json={'event_type': 'BOARDED'}).status_code == 403
    parent.role = 'DRIVER'
    other = Bus(plate_no='OTHER', device_id='other', route_name='Other'); db.add(other); db.flush()
    driver = Driver(user_id=parent.id, name='Test', phone='1', license_no='SYNTHETIC', nic='TEST', bus_id=other.id, status='ACTIVE')
    db.add(driver); db.commit()
    assert client.post(f'/face-devices/{machine.id}/direction', json={'event_type': 'BOARDED'}).status_code == 403
    driver.bus_id = machine.bus_id; db.commit()
    assert client.post(f'/face-devices/{machine.id}/direction', json={'event_type': 'ALIGHTED'}).status_code == 200
    assert client.get('/admin/face-events').status_code == 403


def test_unverified_clock_never_uses_current_mode_for_old_scan(setup):
    db, machine, _, _, client = setup
    machine.clock_checked_at = machine.clock_verified_until = None; db.commit()
    row = process(db, ingest(db, record()).id)
    assert row.processing_status == 'PENDING' and 'clock' in row.processing_error
    payload = {'valid_until': (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(),
               'observed_error_seconds': 2, 'evidence': 'Synthetic physical check'}
    assert client.post(f'/admin/face-devices/{machine.id}/clock-check', json=payload).status_code == 200
    assert process(db, row.id).processing_status == 'PENDING'
    payload['valid_until'] = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
    assert client.post(f'/admin/face-devices/{machine.id}/clock-check', json=payload).status_code == 422


def test_notification_uncertain_requires_audited_reconciliation(setup, monkeypatch):
    from app.models.payroll import AuditLog
    db, _, _, _, client = setup
    process(db, ingest(db, record()).id)
    job = db.query(FaceNotificationJob).one()
    calls = []
    def interrupted(*args, **kwargs):
        calls.append(1); raise RuntimeError('synthetic provider timeout')
    monkeypatch.setattr('app.services.notification_service.send_event_notifications', interrupted)
    deliver_job(db, job.id); deliver_job(db, job.id)
    assert job.status == 'UNCERTAIN' and len(calls) == 1
    payload = {'resolution': 'DELIVERED', 'evidence': 'Synthetic provider confirms delivery; worker stopped'}
    assert client.post(f'/admin/face-notifications/{job.id}/reconcile', json=payload).json()['status'] == 'SENT'
    assert db.query(AuditLog).filter_by(action='FACE_NOTIFICATION_RECONCILE').count() == 1
    assert client.post(f'/admin/face-notifications/{job.id}/reconcile', json=payload | {'resolution': 'RETRY'}).status_code == 409


def test_ingestion_commit_failure_is_not_accepted(setup, monkeypatch):
    db, *_ = setup
    original_commit = db.commit
    def fail(): raise RuntimeError('Synthetic commit failure')
    monkeypatch.setattr(db, 'commit', fail)
    with pytest.raises(RuntimeError): ingest(db, record())
    db.rollback(); monkeypatch.setattr(db, 'commit', original_commit)
    assert db.query(FaceInbox).count() == 0
    assert ingest(db, record()).id is not None


def test_managed_device_cannot_bypass_adapter_using_legacy_receiver(setup):
    from app.api.routes.zkteco import router as legacy_router
    db, machine, _, _, client = setup
    client.app.include_router(legacy_router)
    assert client.post('/iclock/cdata?SN=SYNTHETIC-1&table=ATTLOG', content=record().raw).status_code == 409
    assert db.query(Event).count() == 0


def test_adapter_requires_encryption_configuration(setup, monkeypatch):
    *_, client = setup
    monkeypatch.setattr(get_settings(), 'FACE_ADAPTER_TOKEN', 'synthetic-secret')
    monkeypatch.setattr(get_settings(), 'FACE_RAW_ENCRYPTION_KEY', '')
    assert client.post('/internal/face-receiver/records', json=record().model_dump(),
                       headers={'x-face-adapter-token': 'synthetic-secret'}).status_code == 503


def test_gps_timezone_normalizes_at_ingestion(setup):
    from app.services.device_service import save_bus_location
    db, machine, *_ = setup
    local = datetime(2026, 10, 20, 7, 30, tzinfo=timezone(timedelta(hours=5, minutes=30)))
    fix = save_bus_location(db, machine.bus_id, 6, 80, None, None, local, 5)
    assert fix.gps_time == NOW
    row = process(db, ingest(db, record()).id)
    assert db.get(Event, row.event_id).gps_status == 'VALID'


def test_concurrent_processing_creates_one_event_and_job(setup, tmp_path):
    source, *_ = setup
    engine = create_engine(f'sqlite:///{tmp_path}/processing.db', connect_args={'timeout': 20})
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        for model in (Bus, Student, Parent, ParentStudent, StudentTransport, FaceTerminal, FaceEnrollment, FaceDirection):
            for obj in source.query(model).all():
                db.add(model(**{c.key: getattr(obj, c.key) for c in model.__table__.columns}))
            db.flush()
        db.commit()
        inbox_id = ingest(db, record()).id
    def worker(_):
        with Session(engine) as db: return process(db, inbox_id).event_id
    with ThreadPoolExecutor(max_workers=4) as pool:
        ids = list(pool.map(worker, range(8)))
    assert len(set(ids)) == 1
    with Session(engine) as db:
        assert db.query(Event).count() == db.query(FaceNotificationJob).count() == 1
    engine.dispose()
