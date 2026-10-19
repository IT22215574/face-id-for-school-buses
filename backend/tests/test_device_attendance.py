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


def test_two_machines_per_bus_fixed_directions_and_driver_isolation(setup):
    from app.api.deps import require_parent
    from app.api.routes.face_terminals import router as machines_router
    from app.models.payroll import Driver
    from app.models.face_terminal import FaceTerminal
    client, db, student, parent, device = setup
    parent.role = 'DRIVER'
    db.add(Driver(user_id=parent.id, name='Driver', phone='1', license_no='L1', nic='N1', bus_id=device.bus_id, status='ACTIVE'))
    other_bus = Bus(plate_no='SECOND', device_id='second-bus', route_name='Second')
    other_driver = Parent(name='Other driver', email='driver2@test.com', phone='2', role='DRIVER', password_hash='x')
    db.add_all([other_bus, other_driver])
    db.flush()
    db.add(Driver(user_id=other_driver.id, name='Other driver', phone='2', license_no='L2', nic='N2', bus_id=other_bus.id, status='ACTIVE'))
    db.commit()
    client.app.include_router(machines_router)
    user = [parent]
    client.app.dependency_overrides[require_parent] = lambda: user[0]
    def payload(serial, pin='1001', mapped=True):
        return {'serial': serial, 'model': 'ZKTeco test', 'timezone': 'Asia/Colombo',
                'students': {pin: student.id} if mapped else {}}
    assert client.put('/driver/machines/ENTRY', json=payload('BUS1-IN')).status_code == 200
    assert client.put('/driver/machines/EXIT', json=payload('BUS1-OUT', '2001')).status_code == 200
    assert len(client.get('/driver/machines').json()['machines']) == 2
    for serial, pin in [('BUS1-IN', '1001'), ('BUS1-OUT', '2001')]:
        result = client.post(f'/iclock/cdata?SN={serial}&table=ATTLOG', content=f'{pin}\t2026-10-19 07:30:00\t0\t15')
        assert result.status_code == 200, result.text
    assert {e.event_type.value for e in db.query(Event).all()} == {'BOARDED', 'ALIGHTED'}
    assert client.get('/driver/machines').json()['machines'][0]['last_seen_at'] is not None
    user[0] = other_driver
    assert client.get('/driver/machines').json()['machines'] == []
    assert client.put('/driver/machines/ENTRY', json=payload('BUS1-IN', mapped=False)).status_code == 409
    assert client.put('/driver/machines/ENTRY', json=payload('BUS2-IN')).status_code == 403
    assert client.put('/driver/machines/ENTRY', json=payload('BUS2-IN', mapped=False)).status_code == 200
    assert client.delete('/driver/machines/EXIT').status_code == 200
    assert db.query(FaceTerminal).filter_by(serial='BUS1-OUT').first() is not None
    user[0] = parent
    assert client.delete('/driver/machines/ENTRY').status_code == 200
    assert client.post('/iclock/cdata?SN=BUS1-IN&table=ATTLOG', content='').status_code == 403
    assert db.query(Event).count() == 2
    parent.role = 'PARENT'
    db.commit()
    assert client.get('/driver/machines').status_code == 403
