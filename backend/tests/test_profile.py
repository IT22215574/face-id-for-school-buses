import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models import Parent, Driver
from app.api.routes.parents import update_me
from app.schemas.parent import ProfileUpdate


@pytest.mark.parametrize('role', ['PARENT', 'DRIVER'])
def test_profile_update_persists_and_rejects_duplicate_contact(role):
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        account = Parent(name='Original', email='one@example.com', phone='12345678', role=role, password_hash='unchanged')
        other = Parent(name='Other', email='other@example.com', phone='87654321', password_hash='x')
        db.add_all([account, other])
        db.flush()
        if role == 'DRIVER':
            db.add(Driver(user_id=account.id, name=account.name, phone=account.phone, license_no='L', nic='N', status='ACTIVE'))
        db.commit()
        saved = update_me(ProfileUpdate(name=' Updated ', phone='11223344', email='new@example.com'), account, db)
        assert saved.name == 'Updated'
        assert saved.role == role
        assert saved.password_hash == 'unchanged'
        if role == 'DRIVER':
            driver = db.query(Driver).one()
            assert (driver.name, driver.phone) == ('Updated', '11223344')
        with pytest.raises(HTTPException) as error:
            update_me(ProfileUpdate(name='Updated', phone='11223344', email=other.email), account, db)
        assert error.value.status_code == 409
        db.refresh(account)
        assert account.email == 'new@example.com'
    engine.dispose()


def test_profile_cannot_change_role_or_accept_blank_name():
    with pytest.raises(ValidationError):
        ProfileUpdate(name='Valid', phone='12345678', email='a@example.com', role='ADMIN')
    with pytest.raises(ValidationError):
        ProfileUpdate(name='  ', phone='12345678', email='a@example.com')
