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

    device_name: Mapped[str | None] = mapped_column(String(100))
    firmware_version: Mapped[str | None] = mapped_column(String(100))
    enabled: Mapped[bool] = mapped_column(default=True, server_default='1')
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    clock_checked_at: Mapped[datetime | None]
    clock_verified_until: Mapped[datetime | None]
    adapter_managed: Mapped[bool] = mapped_column(default=False, server_default="0")
