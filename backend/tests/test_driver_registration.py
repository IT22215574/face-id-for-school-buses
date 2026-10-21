import base64
import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.db.base import Base
from app.models import Parent, Bus, Driver
from app.models.driver_registration import DriverRegistration
from app.schemas.driver_registration import DriverRegistrationCreate
from app.api.routes.admin import register_driver, driver_registration_details
from app.api.deps import require_admin
from app.core.encryption import decrypt_text, settings


def values():
    photo = 'data:image/png;base64,' + base64.b64encode(b'\x89PNG\r\n\x1a\nexample').decode()
    return dict(name='Test Driver', phone='0771234567', email='DRIVER@example.com', nic='123456789V', address='School Road', id_front=photo, id_back=photo, password='password123', license_front=photo, bus_id=1)


@pytest.mark.parametrize('field,value', [('name', ' '), ('phone', 'abc1234567'), ('phone', '+94771234567'), ('phone', '07712345678'), ('nic', '123456789X'), ('nic', 'V123456789'), ('email', 'invalid'), ('id_front', 'bad'), ('license_front', 'bad'), ('license_front', None), ('id_back', 'data:image/png;base64,aGVsbG8='), ('password', '12345678'), ('bus_id', 0), ('address', ' ')])
def test_validation(field, value):
    data = values()
    data[field] = value
    with pytest.raises(ValidationError):
        DriverRegistrationCreate(**data)


def test_registration_account_assignment_and_encryption(monkeypatch):
    monkeypatch.setattr(settings, 'ENCRYPTION_KEY', 'test-encryption-key')
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        admin = Parent(name='Admin', phone='0770000000', email='admin@example.com', password_hash='x', role='ADMIN')
        db.add_all([admin, Bus(plate_no='BUS1', device_id='DEV1', route_name='School route')])
        db.commit()
        data = values()
        assistant = {k: v for k, v in values().items() if k not in {'bus_id', 'license_front', 'password'}}
        assistant.update(name='Bus Assistant', email='assistant@example.com', phone='0772345678', nic='987654321V')
        data['assistant'] = assistant
        result = register_driver(DriverRegistrationCreate(**data), db, admin)
        driver = db.get(Driver, result['id'])
        assert driver.user.role == 'DRIVER'
        assert driver.user.email == 'driver@example.com'
        assert driver.user.password_hash != 'password123'
        assert driver.bus_id == 1
        assert driver.license_no == ''
        details = driver_registration_details(driver.id, db, admin)
        assert details['license_front'] == data['license_front']
        record = db.get(DriverRegistration, driver.id)
        assert data['license_front'] not in record.encrypted_details
        assert 'School Road' not in record.encrypted_details
        assert 'School Road' in decrypt_text(record.encrypted_details)
        assert 'Bus Assistant' not in record.encrypted_details
        assert driver_registration_details(driver.id, db, admin)['assistant']['name'] == 'Bus Assistant'
        with pytest.raises(HTTPException) as exc:
            register_driver(DriverRegistrationCreate(**values()), db, admin)
        assert exc.value.status_code == 409
        assert db.query(Driver).count() == 1
        other = values() | dict(email='other@example.com', phone='0772345678', nic='987654321V')
        with pytest.raises(HTTPException) as exc:
            register_driver(DriverRegistrationCreate(**other), db, admin)
        assert exc.value.status_code == 409
        other['bus_id'] = 999
        with pytest.raises(HTTPException) as exc:
            register_driver(DriverRegistrationCreate(**other), db, admin)
        assert exc.value.status_code == 404
        with pytest.raises(HTTPException):
            require_admin(driver.user)
    engine.dispose()


def test_assistant_requires_complete_valid_details():
    data = values()
    data['assistant'] = {'name': 'Helper'}
    with pytest.raises(ValidationError):
        DriverRegistrationCreate(**data)
    assistant = {k: v for k, v in values().items() if k not in {'bus_id', 'license_front', 'password'}}
    assistant.update(name='Bus Assistant', email='assistant@example.com', phone='0772345678', nic='987654321V')
    data['assistant'] = assistant
    assert DriverRegistrationCreate(**data).assistant.name == 'Bus Assistant'
