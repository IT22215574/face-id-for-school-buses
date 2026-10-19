import json
from datetime import datetime, timezone

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.api.routes.zkteco import router
from app.api.routes.devices import ingest_event
from app.api.routes.students import list_student_events
from app.core.config import get_settings
from app.db.base import Base
from app.models import Bus, Device, Event, Parent, ParentStudent, Student
from app.models.student_transport import StudentTransport
from app.schemas.device import DeviceEventIn


@pytest.fixture
def setup(monkeypatch):
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        bus = Bus(plate_no='REAL', device_id='ZK-TEST', route_name='Route')
        student = Student(name='Actual student', grade='5', school_id='School')
        parent = Parent(name='Parent', email='parent@real.test', phone='1', role='PARENT', password_hash='x')
        db.add_all([bus, student, parent])
        db.flush()
        device = Device(bus_id=bus.id, api_key_hash='test-hash', status='ACTIVE')
        db.add_all([device, StudentTransport(student_id=student.id, bus_id=bus.id), ParentStudent(student_id=student.id, parent_id=parent.id)])
        db.commit()
        monkeypatch.setattr(get_settings(), 'ZKTECO_DEVICES_JSON', json.dumps({'ZK-TEST': {
            'bus_id': bus.id, 'students': {'1001': student.id}, 'timezone': 'Asia/Colombo'}}))
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_db] = lambda: db
        with TestClient(app) as client:
            yield client, db, student, parent, device
    engine.dispose()


def test_cloud_scans_are_per_student_utc_and_replay_safe(setup):
    client, db, student, parent, device = setup
    url = '/iclock/cdata?SN=ZK-TEST&table=ATTLOG'
    raw = '1001\t2026-10-19 07:30:00\t0\t15\n1001\t2026-10-19 08:15:00\t1\t15'
    assert client.get('/iclock/cdata?SN=ZK-TEST').status_code == 200
    for _ in range(2):
        assert client.post(url, content=raw).text == 'OK: 2'
    assert db.query(Event).count() == 2
    events = list_student_events(student.id, None, None, parent, db)
    assert events[0]['event_type'] == 'ALIGHTED'
    assert events[1]['event_time'] == '2026-10-19T02:00:00+00:00'
    assert events[1]['lat'] is None
    stranger = Parent(name='Other', email='other@test.com', phone='2', role='PARENT', password_hash='x')
    db.add(stranger)
    db.commit()
    with pytest.raises(HTTPException) as exc:
        list_student_events(student.id, None, None, stranger, db)
    assert exc.value.status_code == 403


def test_invalid_cloud_batches_write_nothing(setup):
    client, db, *_ = setup
    url = '/iclock/cdata?SN=ZK-TEST&table=ATTLOG'
    for row in ['999\t2026-10-19 07:30:00\t0\t15', '1001\tbad-time\t0\t15', '1001\t2026-10-19 07:30:00\t5\t15']:
        assert client.post(url, content='1001\t2026-10-19 07:00:00\t0\t15\n' + row).status_code == 422
        assert db.query(Event).count() == 0
    assert client.post('/iclock/cdata?SN=UNKNOWN&table=ATTLOG', content='').status_code == 403


def test_device_cannot_report_another_bus(setup):
    _, db, student, _, device = setup
    payload = DeviceEventIn(student_id=student.id, bus_id=device.bus_id + 1,
        event_type='BOARDED', event_time=datetime.now(timezone.utc), lat=0, lng=0)
    with pytest.raises(HTTPException) as exc:
        ingest_event(payload, device, db)
    assert exc.value.status_code == 403
    for overrides in [{'event_type': 'unknown'}, {'event_time': datetime.now()}, {'lat': 91}]:
        with pytest.raises(ValidationError):
            DeviceEventIn(**(payload.model_dump() | overrides))
