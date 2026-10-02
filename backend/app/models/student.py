from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.parent import Parent
    from app.models.parent_student import ParentStudent
    from app.models.event import Event


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    grade: Mapped[str] = mapped_column(String(30), nullable=False, default="N/A")
    school_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc), nullable=False)

    parents: Mapped[list["Parent"]] = relationship(
        "Parent",
        secondary="parent_student",
        back_populates="students",
        lazy="selectin",
    )
    student_links: Mapped[list["ParentStudent"]] = relationship(back_populates="student", cascade="all, delete-orphan")
    events: Mapped[list["Event"]] = relationship(back_populates="student", cascade="all, delete-orphan")
    notifications: Mapped[list["Notification"]] = relationship(back_populates="student", cascade="all, delete-orphan")
