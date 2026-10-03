from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.parent import Parent
    from app.models.bus import Bus
    from app.models.payroll import Driver


class EmergencyAlert(Base):
    __tablename__ = "emergency_alerts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    bus_id: Mapped[int] = mapped_column(ForeignKey("buses.id"), nullable=False, index=True)
    driver_id: Mapped[int | None] = mapped_column(ForeignKey("drivers.id"), nullable=True, index=True)
    triggered_by_user_id: Mapped[int] = mapped_column(ForeignKey("parents.id"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(32), default="SOS", nullable=False)
    severity: Mapped[str] = mapped_column(String(16), default="CRITICAL", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="OPEN", nullable=False)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(32), default="DRIVER_APP", nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc), nullable=False)
    acknowledged_by: Mapped[int | None] = mapped_column(ForeignKey("parents.id"), nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(nullable=True)
    resolved_by: Mapped[int | None] = mapped_column(ForeignKey("parents.id"), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(nullable=True)
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    bus: Mapped["Bus"] = relationship("Bus")
    driver: Mapped["Driver | None"] = relationship("Driver", back_populates="emergency_alerts")
    triggered_by: Mapped["Parent"] = relationship("Parent", foreign_keys=[triggered_by_user_id])
    acknowledged_user: Mapped["Parent | None"] = relationship("Parent", foreign_keys=[acknowledged_by])
    resolved_user: Mapped["Parent | None"] = relationship("Parent", foreign_keys=[resolved_by])
    updates: Mapped[list["EmergencyAlertUpdate"]] = relationship(back_populates="alert", cascade="all, delete-orphan")
    notifications: Mapped[list["EmergencyNotification"]] = relationship(back_populates="alert", cascade="all, delete-orphan")


class EmergencyAlertUpdate(Base):
    __tablename__ = "emergency_alert_updates"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    alert_id: Mapped[int] = mapped_column(ForeignKey("emergency_alerts.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("parents.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc), nullable=False)

    alert: Mapped["EmergencyAlert"] = relationship(back_populates="updates")


class EmergencyContact(Base):
    __tablename__ = "emergency_contacts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    school_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone: Mapped[str] = mapped_column(String(32), nullable=False)
    role: Mapped[str] = mapped_column(String(40), default="COORDINATOR", nullable=False)
    priority_order: Mapped[int] = mapped_column(default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc), nullable=False)


class EmergencyNotification(Base):
    __tablename__ = "emergency_notifications"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    alert_id: Mapped[int] = mapped_column(ForeignKey("emergency_alerts.id"), nullable=False, index=True)
    recipient_user_id: Mapped[int | None] = mapped_column(ForeignKey("parents.id"), nullable=True, index=True)
    recipient_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    channel: Mapped[str] = mapped_column(String(12), default="PUSH", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="PENDING", nullable=False)
    attempt_no: Mapped[int] = mapped_column(default=1, nullable=False)
    provider_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc), nullable=False)

    alert: Mapped["EmergencyAlert"] = relationship(back_populates="notifications")
