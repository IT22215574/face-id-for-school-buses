import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.routes.admin import create_bus, list_buses, update_bus
from app.db.base import Base
from app.schemas.admin import BusCreate


def test_saved_routes_can_be_listed_edited_and_reloaded():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        bus = create_bus(BusCreate(plate_no='BUS-1', device_id='DEV-1', route_name='School route'), db, None)
        bus_id = bus.id
        create_bus(BusCreate(plate_no='BUS-2', device_id='DEV-2', route_name='Other route'), db, None)
        update_bus(bus_id, BusCreate(plate_no='BUS-3', device_id='DEV-3', route_name='Updated route'), db, None)
        db.expire_all()
        saved = next(bus for bus in list_buses(db, None) if bus.id == bus_id)
        assert (saved.plate_no, saved.device_id, saved.route_name) == ('BUS-3', 'DEV-3', 'Updated route')
        with pytest.raises(HTTPException) as exc:
            update_bus(bus_id, BusCreate(plate_no='BUS-2', device_id='DEV-3', route_name='Duplicate'), db, None)
        assert exc.value.status_code == 409
        db.expire_all()
        assert saved.plate_no == 'BUS-3'
        assert saved.route_name == 'Updated route'
