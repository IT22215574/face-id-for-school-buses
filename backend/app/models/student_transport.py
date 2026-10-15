from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class StudentTransport(Base):
    __tablename__ = "student_transport"
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), primary_key=True)
    bus_id: Mapped[int] = mapped_column(ForeignKey("buses.id"), index=True, nullable=False)
