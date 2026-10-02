from app.db.base import Base
from app.models import *  # noqa: F401,F403
from app.db.session import engine


def create_all_tables() -> None:
    Base.metadata.create_all(bind=engine)
