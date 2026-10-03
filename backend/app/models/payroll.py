from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.parent import Parent
    from app.models.bus import Bus


class Driver(Base):
    __tablename__ = "drivers"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("parents.id"), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone: Mapped[str] = mapped_column(String(32), nullable=False)
    license_no: Mapped[str] = mapped_column(String(80), nullable=False)
    nic: Mapped[str] = mapped_column(String(30), nullable=False)
    bus_id: Mapped[int | None] = mapped_column(ForeignKey("buses.id"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc), nullable=False)

    user: Mapped["Parent"] = relationship("Parent")
    bus: Mapped["Bus | None"] = relationship("Bus")
    payroll_records: Mapped[list["PayrollRecord"]] = relationship(back_populates="driver", cascade="all, delete-orphan")
    trip_history: Mapped[list["Trip"]] = relationship(back_populates="driver", cascade="all, delete-orphan")
    attendance_history: Mapped[list["DriverAttendance"]] = relationship(back_populates="driver", cascade="all, delete-orphan")
    advances: Mapped[list["DriverAdvance"]] = relationship(back_populates="driver", cascade="all, delete-orphan")
    adjustments: Mapped[list["DriverAdjustment"]] = relationship(back_populates="driver", cascade="all, delete-orphan")
    pay_profiles: Mapped[list["DriverPayProfile"]] = relationship(back_populates="driver", cascade="all, delete-orphan")
    emergency_alerts: Mapped[list["EmergencyAlert"]] = relationship(back_populates="driver")


class DriverPayProfile(Base):
    __tablename__ = "driver_pay_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    driver_id: Mapped[int] = mapped_column(ForeignKey("drivers.id"), nullable=False, index=True)
    pay_type: Mapped[str] = mapped_column(String(32), nullable=False, default="MONTHLY_SALARY")
    base_salary: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    per_trip_rate: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    per_km_rate: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    overtime_rate: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    bank_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    bank_account_no_encrypted: Mapped[str | None] = mapped_column(String(255), nullable=True)
    effective_from: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc), nullable=False)
    effective_to: Mapped[datetime | None] = mapped_column(nullable=True)

    driver: Mapped["Driver"] = relationship(back_populates="pay_profiles")


class Trip(Base):
    __tablename__ = "trips"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    bus_id: Mapped[int] = mapped_column(ForeignKey("buses.id"), nullable=False, index=True)
    driver_id: Mapped[int] = mapped_column(ForeignKey("drivers.id"), nullable=False, index=True)
    route_name: Mapped[str] = mapped_column(String(120), nullable=False)
    shift: Mapped[str] = mapped_column(String(20), default="MORNING", nullable=False)
    start_time: Mapped[datetime] = mapped_column(nullable=False)
    end_time: Mapped[datetime | None] = mapped_column(nullable=True)
    distance_km: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="COMPLETED", nullable=False)

    driver: Mapped["Driver"] = relationship(back_populates="trip_history")


class DriverAttendance(Base):
    __tablename__ = "driver_attendance"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    driver_id: Mapped[int] = mapped_column(ForeignKey("drivers.id"), nullable=False, index=True)
    date: Mapped[datetime] = mapped_column(nullable=False)
    check_in: Mapped[datetime | None] = mapped_column(nullable=True)
    check_out: Mapped[datetime | None] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="PRESENT", nullable=False)

    driver: Mapped["Driver"] = relationship(back_populates="attendance_history")


class PayPeriod(Base):
    __tablename__ = "pay_periods"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    month: Mapped[int] = mapped_column(nullable=False)
    year: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="OPEN", nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc), nullable=False)

    payroll_records: Mapped[list["PayrollRecord"]] = relationship(back_populates="pay_period", cascade="all, delete-orphan")


class PayrollRecord(Base):
    __tablename__ = "payroll_records"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    driver_id: Mapped[int] = mapped_column(ForeignKey("drivers.id"), nullable=False, index=True)
    pay_period_id: Mapped[int] = mapped_column(ForeignKey("pay_periods.id"), nullable=False, index=True)
    base_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    trip_earnings: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    distance_earnings: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    overtime_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    bonus: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    allowances: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    advance_deduction: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    penalty_deduction: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    other_deduction: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    gross: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    net: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="DRAFT", nullable=False)
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("parents.id"), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(nullable=True)
    payment_method: Mapped[str | None] = mapped_column(String(20), nullable=True)
    payment_reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc), nullable=False)

    driver: Mapped["Driver"] = relationship(back_populates="payroll_records")
    pay_period: Mapped["PayPeriod"] = relationship(back_populates="payroll_records")
    payslip: Mapped["Payslip | None"] = relationship(back_populates="payroll_record", uselist=False, cascade="all, delete-orphan")


class DriverAdvance(Base):
    __tablename__ = "driver_advances"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    driver_id: Mapped[int] = mapped_column(ForeignKey("drivers.id"), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    issued_date: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc), nullable=False)
    remaining_balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    monthly_recovery: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)

    driver: Mapped["Driver"] = relationship(back_populates="advances")


class DriverAdjustment(Base):
    __tablename__ = "driver_adjustments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    driver_id: Mapped[int] = mapped_column(ForeignKey("drivers.id"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    date: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc), nullable=False)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("parents.id"), nullable=True)

    driver: Mapped["Driver"] = relationship(back_populates="adjustments")


class Payslip(Base):
    __tablename__ = "payslips"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    payroll_record_id: Mapped[int] = mapped_column(ForeignKey("payroll_records.id"), nullable=False, unique=True, index=True)
    pdf_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    generated_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc), nullable=False)

    payroll_record: Mapped["PayrollRecord"] = relationship(back_populates="payslip")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("parents.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    entity: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[int | None] = mapped_column(nullable=True)
    before_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    after_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc), nullable=False)
