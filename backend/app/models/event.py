from datetime import datetime, timezone
from enum import Enum as PyEnum
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.bus import Bus
    from app.models.student import Student


class EventType(str, PyEnum):
    BOARDED = "BOARDED"
    ALIGHTED = "ALIGHTED"


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False, index=True)
    bus_id: Mapped[int] = mapped_column(ForeignKey("buses.id"), nullable=False, index=True)
    event_type: Mapped[EventType] = mapped_column(SAEnum(EventType), nullable=False)
    event_time: Mapped[datetime] = mapped_column(nullable=False)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="DEVICE", nullable=False)
    ingestion_key: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc), nullable=False)

    source_device_id: Mapped[int | None] = mapped_column(ForeignKey("face_terminals.id"))
    received_at: Mapped[datetime | None]
    direction_source: Mapped[str | None] = mapped_column(String(30))
    gps_accuracy_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    gps_status: Mapped[str | None] = mapped_column(String(20))
    gps_timestamp: Mapped[datetime | None]
    gps_source: Mapped[str | None] = mapped_column(String(30))
    is_delayed: Mapped[bool | None]

    student: Mapped["Student"] = relationship(back_populates="events")
    bus: Mapped["Bus"] = relationship(back_populates="events")
