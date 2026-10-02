from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ParentStudent(Base):
    __tablename__ = "parent_student"

    parent_id: Mapped[int] = mapped_column(ForeignKey("parents.id"), primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), primary_key=True)

    parent: Mapped["Parent"] = relationship(back_populates="student_links")
    student: Mapped["Student"] = relationship(back_populates="student_links")
