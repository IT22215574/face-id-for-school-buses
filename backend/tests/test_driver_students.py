import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db.base import Base
from app.models import Parent, Driver, Bus, Student
from app.models.parent_student import ParentStudent
from app.models.student_transport import StudentTransport
from app.api.routes.buses import DriverStudentIn, add_driver_student
from app.api.routes.parents import read_my_transport


def test_driver_adds_child_to_own_vehicle_and_parent_account():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        parent = Parent(name='Parent', email='parent@example.com', phone='12345678', password_hash='x')
        user = Parent(name='Driver', email='driver@example.com', phone='87654321', role='DRIVER', password_hash='x')
        bus = Bus(plate_no='BUS-1', device_id='device-1', route_name='School route')
        db.add_all([parent, user, bus])
        db.flush()
        driver = Driver(user_id=user.id, bus_id=bus.id, name='Driver', phone='87654321', license_no='L', nic='N', status='ACTIVE')
        db.add(driver)
        db.commit()
        payload = DriverStudentIn(name=' Child ', grade='3', school_id='KUR-MALIYADEVA', parent_email='PARENT@example.com', father_phone='0711234567', mother_phone='+94 771234567')
        result = add_driver_student(payload, user, db)
        assert result['bus_id'] == bus.id
        assert db.get(StudentTransport, result['id']).bus_id == bus.id
        assert db.get(ParentStudent, (parent.id, result['id'])) is not None
        assert read_my_transport(user, db)[0]['name'] == 'Child'
        assert read_my_transport(user, db)[0]['father_phone'] == '0711234567'
        assert read_my_transport(parent, db)[0]['mother_phone'] == '+94 771234567'
        assert read_my_transport(parent, db)[0]['id'] == result['id']
        with pytest.raises(HTTPException) as error:
            add_driver_student(payload, parent, db)
        assert error.value.status_code == 403
        payload.parent_email = 'missing@example.com'
        with pytest.raises(HTTPException) as error:
            add_driver_student(payload, user, db)
        assert error.value.status_code == 404
        assert db.query(Student).count() == 1
        driver.bus_id = None
        db.commit()
        with pytest.raises(HTTPException) as error:
            add_driver_student(payload, user, db)
        assert error.value.status_code == 403
    engine.dispose()


def test_parent_phone_numbers_are_optional_and_validated():
    from pydantic import ValidationError
    values = dict(name='Child', grade='3', school_id='KUR-MALIYADEVA', parent_email='p@example.com')
    assert DriverStudentIn(**values).father_phone == ''
    assert DriverStudentIn(**values).mother_phone == ''
    for field in ['father_phone', 'mother_phone']:
        with pytest.raises(ValidationError):
            DriverStudentIn(**values, **{field: 'invalid'})
