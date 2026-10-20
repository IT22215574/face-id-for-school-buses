import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.parent import Parent
from app.models.student import Student
from app.models.parent_student import ParentStudent
from app.api.routes.students import get_student_status, list_student_events


@pytest.mark.parametrize('endpoint', [get_student_status, list_student_events])
def test_parent_student_access_across_auth_and_request_sessions(endpoint):
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    with Session(engine) as setup:
        parent = Parent(name='Parent', phone='123', email='linked@example.com', password_hash='x')
        child = Student(name='Child', grade='5', school_id='TEST')
        other = Student(name='Other child', grade='6', school_id='TEST')
        setup.add_all([parent, child, other])
        setup.flush()
        setup.add(ParentStudent(parent_id=parent.id, student_id=child.id))
        setup.commit()
        parent_id, child_id, other_id = parent.id, child.id, other.id
    # Authentication and route dependencies use distinct SQLAlchemy sessions.
    with Session(engine) as auth_session, Session(engine) as request_session:
        account = auth_session.get(Parent, parent_id)
        assert endpoint(child_id, current_parent=account, db=request_session, **({"from_": None, "to": None} if endpoint == list_student_events else {})) is not None
        with pytest.raises(HTTPException) as error:
            endpoint(other_id, current_parent=account, db=request_session, **({"from_": None, "to": None} if endpoint == list_student_events else {}))
        assert error.value.status_code == 403
    engine.dispose()
