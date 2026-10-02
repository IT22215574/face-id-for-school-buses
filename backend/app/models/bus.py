from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.device import Device
    from app.models.bus_location import BusLocation


class Bus(Base):
    __tablename__ = "buses"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    plate_no: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    device_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    route_name: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc), nullable=False)

    device: Mapped["Device"] = relationship(back_populates="bus", uselist=False)
    locations: Mapped[list["BusLocation"]] = relationship(back_populates="bus", cascade="all, delete-orphan")
    events: Mapped[list["Event"]] = relationship(back_populates="bus", cascade="all, delete-orphan")
