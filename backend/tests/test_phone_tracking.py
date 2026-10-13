from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.api.routes.buses import PhoneLocationIn, assigned_driver_bus, share_phone_location, read_bus_live_location
from app.models.bus import Bus
from app.models.parent import Parent
from app.models.payroll import Driver


@pytest.fixture
def db():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def test_only_active_assigned_driver_can_share(db):
    bus = Bus(plate_no='TEST-1', device_id='test-device', route_name='Test route')
    user = Parent(name='Driver', phone='123', email='test@example.com', password_hash='x', role='DRIVER')
    db.add_all([bus, user])
    db.flush()
    driver = Driver(user_id=user.id, name='Driver', phone='123', license_no='L1', nic='N1', bus_id=bus.id, status='ACTIVE')
    db.add(driver)
    db.commit()
    payload = PhoneLocationIn(lat=6.9271, lng=79.8612, gps_time=datetime.now(timezone.utc))
    result = share_phone_location(payload, user, db)
    assert result['bus_id'] == bus.id
    location = read_bus_live_location(bus.id, user, db)
    assert location.lat == payload.lat
    assert location.lng == payload.lng
    driver.status = 'INACTIVE'
    db.commit()
    with pytest.raises(HTTPException) as error:
        share_phone_location(payload, user, db)
    assert error.value.status_code == 403


def test_parent_and_unassigned_driver_are_rejected(db):
    for user in [SimpleNamespace(id=1, role='PARENT'), SimpleNamespace(id=2, role='DRIVER')]:
        with pytest.raises(HTTPException) as error:
            assigned_driver_bus(user, db)
        assert error.value.status_code == 403


@pytest.mark.parametrize('values', [{'lat': 91}, {'lng': -181}, {'lat': float('nan')}, {'speed': -1}, {'heading': 360}])
def test_invalid_coordinates_rejected(values):
    with pytest.raises(ValidationError):
        PhoneLocationIn(**({'lat': 0, 'lng': 0, 'gps_time': datetime.now(timezone.utc)} | values))
