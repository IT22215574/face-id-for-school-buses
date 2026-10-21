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


@pytest.fixture
def driver_db(monkeypatch):
    from sqlalchemy import event
    monkeypatch.setattr(settings, 'ENCRYPTION_KEY', 'test-encryption-key')
    engine = create_engine('sqlite:///:memory:')
    @event.listens_for(engine, 'connect')
    def enable_foreign_keys(connection, _):
        connection.execute('PRAGMA foreign_keys=ON')
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all([Bus(plate_no='BUS1', device_id='DEV1', route_name='School route'),
                    Bus(plate_no='BUS2', device_id='DEV2', route_name='Second route')])
        db.commit()
        result = register_driver(DriverRegistrationCreate(**values()), db, None)
        yield db, result['id']


def test_edit_driver_preserves_password_and_updates_encrypted_details(driver_db):
    from app.api.routes.admin import update_driver_registration
    from app.schemas.driver_registration import DriverRegistrationUpdate
    from app.core.security import verify_password
    db, driver_id = driver_db
    user = db.get(Driver, driver_id).user
    old_hash = user.password_hash
    data = values() | dict(name='Updated Driver', email='updated@example.com', phone='0779999999', bus_id=2, address='New School Road')
    data.pop('password')
    update_driver_registration(driver_id, DriverRegistrationUpdate(**data), db, None)
    db.expire_all()
    driver = db.get(Driver, driver_id)
    assert driver.name == driver.user.name == 'Updated Driver'
    assert driver.phone == driver.user.phone == '0779999999'
    assert driver.user.email == 'updated@example.com'
    assert driver.bus_id == 2
    assert driver.user.password_hash == old_hash
    assert driver_registration_details(driver_id, db, None)['address'] == 'New School Road'
    assert 'New School Road' not in db.get(DriverRegistration, driver_id).encrypted_details
    update_driver_registration(driver_id, DriverRegistrationUpdate(**(data | dict(password='newPassword123'))), db, None)
    assert verify_password('newPassword123', driver.user.password_hash)


def test_edit_rejects_duplicate_assignment_and_contact(driver_db):
    from app.api.routes.admin import update_driver_registration
    from app.schemas.driver_registration import DriverRegistrationUpdate
    db, driver_id = driver_db
    second = values() | dict(name='Other Driver', email='other@example.com', phone='0778888888', nic='987654321V', bus_id=2)
    register_driver(DriverRegistrationCreate(**second), db, None)
    for changes in [dict(bus_id=2), dict(email=second['email']), dict(nic=second['nic'])]:
        with pytest.raises(HTTPException) as exc:
            update_driver_registration(driver_id, DriverRegistrationUpdate(**(values() | changes)), db, None)
        assert exc.value.status_code == 409
    assert db.get(Driver, driver_id).bus_id == 1


def test_delete_driver_removes_login_and_allows_bus_deletion(driver_db):
    from app.api.routes.admin import delete_driver_registration, delete_bus
    db, driver_id = driver_db
    user_id = db.get(Driver, driver_id).user_id
    with pytest.raises(HTTPException) as exc:
        delete_bus(1, db, None)
    assert exc.value.status_code == 409
    delete_driver_registration(driver_id, db, None)
    assert db.get(Driver, driver_id) is None
    assert db.get(DriverRegistration, driver_id) is None
    assert db.get(Parent, user_id) is None
    delete_bus(1, db, None)
    assert db.get(Bus, 1) is None


def test_delete_driver_with_payroll_history_is_blocked(driver_db):
    from app.api.routes.admin import delete_driver_registration
    from app.models.payroll import DriverAdvance
    db, driver_id = driver_db
    db.add(DriverAdvance(driver_id=driver_id, amount=100, reason='Advance'))
    db.commit()
    with pytest.raises(HTTPException) as exc:
        delete_driver_registration(driver_id, db, None)
    assert exc.value.status_code == 409
    assert db.get(Driver, driver_id) is not None


def test_photo_limit_accepts_five_mb_and_rejects_larger():
    photo = b'\x89PNG\r\n\x1a\n' + b'x' * (5 * 1024 * 1024 - 8)
    data = values() | dict(id_front='data:image/png;base64,' + base64.b64encode(photo).decode())
    assert DriverRegistrationCreate(**data).id_front == data['id_front']
    data['id_front'] = 'data:image/png;base64,' + base64.b64encode(photo + b'x').decode()
    with pytest.raises(ValidationError):
        DriverRegistrationCreate(**data)
