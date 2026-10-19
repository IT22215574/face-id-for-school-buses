from datetime import datetime
from sqlalchemy import ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class FaceTerminal(Base):
    __tablename__ = "face_terminals"
    __table_args__ = (UniqueConstraint("bus_id", "role", name="uq_face_terminal_bus_role"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    bus_id: Mapped[int] = mapped_column(ForeignKey("buses.id"), nullable=False, index=True)
    serial: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    role: Mapped[str] = mapped_column(String(10), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    timezone: Mapped[str] = mapped_column(String(80), nullable=False, default="Asia/Colombo")
    students: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    last_seen_at: Mapped[datetime | None] = mapped_column(nullable=True)
