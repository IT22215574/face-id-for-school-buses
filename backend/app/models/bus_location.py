from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.bus import Bus


class BusLocation(Base):
    __tablename__ = "bus_locations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    bus_id: Mapped[int] = mapped_column(ForeignKey("buses.id"), nullable=False, index=True)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)
    speed: Mapped[float | None] = mapped_column(Float, nullable=True)
    heading: Mapped[float | None] = mapped_column(Float, nullable=True)
    gps_time: Mapped[datetime | None] = mapped_column(nullable=True)
    server_time: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc), nullable=False)

    bus: Mapped["Bus"] = relationship(back_populates="locations")
