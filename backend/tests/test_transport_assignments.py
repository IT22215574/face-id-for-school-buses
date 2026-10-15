from datetime import datetime, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models import Parent, Student, ParentStudent, Bus, Driver
from app.api.routes.admin import assign_student_bus
from app.api.routes.parents import read_my_transport
from app.api.routes.buses import PhoneLocationIn, share_phone_location, read_bus_live_location, read_route_history, read_bus_route


def test_assigned_parent_tracks_driver_and_unrelated_parent_cannot():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        parent = Parent(name='Parent', email='parent@test.com', phone='1', role='PARENT', password_hash='x')
        other = Parent(name='Other', email='other@test.com', phone='2', role='PARENT', password_hash='x')
        user = Parent(name='Driver', email='driver@test.com', phone='3', role='DRIVER', password_hash='x')
        child = Student(name='Child', grade='5', school_id='KUR-MALIYADEVA')
        bus = Bus(plate_no='BUS-24', device_id='device', route_name='Kurunegala school loop')
        db.add_all([parent, other, user, child, bus])
        db.flush()
        db.add(ParentStudent(parent_id=parent.id, student_id=child.id))
        db.add(Driver(user_id=user.id, name='Driver', phone='3', license_no='L', nic='N', bus_id=bus.id, status='ACTIVE'))
        db.commit()
        # The administrative endpoint is protected by require_admin in HTTP routing.
        assign_student_bus(child.id, bus.id, db, parent)
        assigned = read_my_transport(parent, db)
        assert assigned[0]['id'] == child.id
        assert assigned[0]['bus_id'] == bus.id
        assert assigned[0]['school']['name'] == 'Maliyadeva College, Kurunegala'
        assert read_my_transport(user, db)[0]['id'] == child.id
        assert read_my_transport(other, db) == []
        payload = PhoneLocationIn(lat=7.4863, lng=80.3647, gps_time=datetime.now(timezone.utc))
        share_phone_location(payload, user, db)
        assert read_bus_live_location(bus.id, parent, db).lat == payload.lat
        assert read_route_history(bus.id, None, None, parent, db)['points']
        assert len(read_bus_route(bus.id, parent, db)['stops']) == 4
        for read in [lambda: read_bus_live_location(bus.id, other, db),
                     lambda: read_route_history(bus.id, None, None, other, db),
                     lambda: read_bus_route(bus.id, other, db)]:
            with pytest.raises(HTTPException) as error:
                read()
            assert error.value.status_code == 403
        unassigned = Bus(plate_no='OTHER', device_id='other', route_name='Other')
        db.add(unassigned)
        db.commit()
        assign_student_bus(child.id, unassigned.id, db, parent)
        with pytest.raises(HTTPException):
            read_bus_live_location(bus.id, parent, db)
    engine.dispose()
