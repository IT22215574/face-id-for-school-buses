from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db.base import Base
from app.models import Parent
from app.core.security import hash_password
from app.services.auth_service import login_parent, refresh_token_pair


def test_refresh_accepts_sqlite_naive_utc_expiry():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(Parent(name='Admin', phone='0770000011', email='refresh@example.com', password_hash=hash_password('password123'), role='ADMIN'))
        db.commit()
        _, refresh, _, _ = login_parent(db, 'refresh@example.com', 'password123')
        access, new_refresh = refresh_token_pair(db, refresh)
        assert access
        assert new_refresh
    engine.dispose()
