from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.parent_student import ParentStudent
    from app.models.student import Student


class Parent(Base):
    __tablename__ = "parents"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    fcm_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(20), default="PARENT", nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc), nullable=False)

    student_links: Mapped[list["ParentStudent"]] = relationship(back_populates="parent", cascade="all, delete-orphan")
    students: Mapped[list["Student"]] = relationship(
        "Student",
        secondary="parent_student",
        back_populates="parents",
        lazy="selectin",
    )
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(back_populates="parent", cascade="all, delete-orphan")
    notifications: Mapped[list["Notification"]] = relationship(back_populates="parent", cascade="all, delete-orphan")
