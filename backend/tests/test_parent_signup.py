import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db.base import Base
from app.models import Parent
from app.models.refresh_token import RefreshToken
from app.schemas.auth import ParentRegister
from app.api.routes.auth import register_user
from app.core.security import decode_token, verify_password


def test_parent_signup_tokens_and_duplicate_contacts():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        payload = ParentRegister(name=' Test Parent ', phone='0771234567',
                                 email='PARENT@example.com', password='password123')
        result = register_user(payload, db)
        parent = db.query(Parent).one()
        assert parent.name == 'Test Parent'
        assert parent.email == 'parent@example.com'
        assert parent.role == 'PARENT'
        assert parent.students == []
        assert verify_password('password123', parent.password_hash)
        assert decode_token(result.access_token)['sub'] == str(parent.id)
        assert decode_token(result.refresh_token)['type'] == 'refresh'
        assert db.query(RefreshToken).count() == 1
        for changes in [dict(phone='0779999999'), dict(email='other@example.com')]:
            with pytest.raises(HTTPException) as exc:
                register_user(payload.model_copy(update=changes), db)
            assert exc.value.status_code == 409
        assert db.query(Parent).count() == 1
    engine.dispose()


@pytest.mark.parametrize('changes', [dict(name='  '), dict(phone='abcdefgh'),
    dict(email='invalid'), dict(password='short'), dict(password='é' * 40)])
def test_signup_rejects_invalid_details(changes):
    with pytest.raises(ValidationError):
        ParentRegister(**(dict(name='Parent', phone='0771234567',
            email='parent@example.com', password='password123') | changes))
