from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.encryption import decrypt_text, encrypt_text, mask_value
from app.models.parent import Parent
from app.models.payroll import AuditLog, Driver, DriverAdvance, DriverAdjustment, DriverAttendance, DriverPayProfile, PayPeriod, PayrollRecord, Payslip, Trip
from app.services.payslip_pdf import generate_payslip_pdf

settings = get_settings()


class PayrollService:
    @staticmethod
    def _snapshot(record: PayrollRecord | None) -> dict[str, Any]:
        if record is None:
            return {}
        return {
            "id": record.id,
            "driver_id": record.driver_id,
            "pay_period_id": record.pay_period_id,
            "base_amount": str(record.base_amount),
            "trip_earnings": str(record.trip_earnings),
            "distance_earnings": str(record.distance_earnings),
            "overtime_amount": str(record.overtime_amount),
            "bonus": str(record.bonus),
            "allowances": str(record.allowances),
            "advance_deduction": str(record.advance_deduction),
            "penalty_deduction": str(record.penalty_deduction),
            "other_deduction": str(record.other_deduction),
            "gross": str(record.gross),
            "net": str(record.net),
            "status": record.status,
            "approved_by": record.approved_by,
            "payment_method": record.payment_method,
            "payment_reference": record.payment_reference,
        }

    @staticmethod
    def _audit(db: Session, user_id: int | None, action: str, entity: str, entity_id: int | None, before: dict[str, Any] | None, after: dict[str, Any] | None) -> None:
        db.add(
            AuditLog(
                user_id=user_id,
                action=action,
                entity=entity,
                entity_id=entity_id,
                before_json=json.dumps(before or {}, default=str),
                after_json=json.dumps(after or {}, default=str),
            )
        )
        db.commit()

    @staticmethod
    def create_pay_period(db: Session, month: int, year: int) -> PayPeriod:
        existing = db.query(PayPeriod).filter(PayPeriod.month == month, PayPeriod.year == year).first()
        if existing:
            return existing
        pay_period = PayPeriod(month=month, year=year, status="OPEN")
        db.add(pay_period)
        db.commit()
        db.refresh(pay_period)
        return pay_period

    @staticmethod
    def upsert_driver_pay_profile(db: Session, driver_id: int, payload: dict[str, Any]):
        driver = db.get(Driver, driver_id)
        if driver is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Driver not found")
        profile = db.query(DriverPayProfile).filter(DriverPayProfile.driver_id == driver_id).order_by(DriverPayProfile.effective_from.desc()).first()
        if profile is None:
            profile = DriverPayProfile(driver_id=driver_id)
        profile.pay_type = payload.get("pay_type", profile.pay_type)
        profile.base_salary = Decimal(str(payload.get("base_salary", profile.base_salary)))
        profile.per_trip_rate = Decimal(str(payload.get("per_trip_rate", profile.per_trip_rate)))
        profile.per_km_rate = Decimal(str(payload.get("per_km_rate", profile.per_km_rate)))
        profile.overtime_rate = Decimal(str(payload.get("overtime_rate", profile.overtime_rate)))
        profile.bank_name = payload.get("bank_name") or profile.bank_name
        if payload.get("bank_account_no"):
            profile.bank_account_no_encrypted = encrypt_text(str(payload["bank_account_no"]))
        profile.effective_from = datetime.fromisoformat(payload["effective_from"]) if payload.get("effective_from") else profile.effective_from
        db.add(profile)
        db.commit()
        db.refresh(profile)
        return profile

    @staticmethod
    def create_advance(db: Session, driver_id: int, amount: Decimal, reason: str, issued_date: str | None = None, monthly_recovery: Decimal | None = None) -> DriverAdvance:
        driver = db.get(Driver, driver_id)
        if driver is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Driver not found")
        advance = DriverAdvance(
            driver_id=driver_id,
            amount=Decimal(str(amount)),
            reason=reason,
            issued_date=datetime.fromisoformat(issued_date) if issued_date else datetime.now(timezone.utc),
            remaining_balance=Decimal(str(amount)),
            monthly_recovery=Decimal(str(monthly_recovery or 0)),
        )
        db.add(advance)
        db.commit()
        db.refresh(advance)
        return advance

    @staticmethod
    def create_adjustment(db: Session, driver_id: int, adjustment_type: str, amount: Decimal, reason: str, date: str | None = None, created_by: int | None = None) -> DriverAdjustment:
        driver = db.get(Driver, driver_id)
        if driver is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Driver not found")
        adjustment = DriverAdjustment(
            driver_id=driver_id,
            type=adjustment_type.upper(),
            amount=Decimal(str(amount)),
            reason=reason,
            date=datetime.fromisoformat(date) if date else datetime.now(timezone.utc),
            created_by=created_by,
        )
        db.add(adjustment)
        db.commit()
        db.refresh(adjustment)
        return adjustment

    @staticmethod
    def _trip_amount_for_driver(db: Session, driver_id: int, pay_period: PayPeriod):
        start = datetime(pay_period.year, pay_period.month, 1, tzinfo=timezone.utc)
        if pay_period.month == 12:
            end = datetime(pay_period.year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            end = datetime(pay_period.year, pay_period.month + 1, 1, tzinfo=timezone.utc)
        trips = db.query(Trip).filter(Trip.driver_id == driver_id, Trip.start_time >= start, Trip.start_time < end).all()
        profile = db.query(DriverPayProfile).filter(DriverPayProfile.driver_id == driver_id).order_by(DriverPayProfile.effective_from.desc()).first()
        if profile is None:
            profile = DriverPayProfile(driver_id=driver_id, base_salary=Decimal("0.00"), per_trip_rate=Decimal("0.00"), per_km_rate=Decimal("0.00"), overtime_rate=Decimal("0.00"))
        trip_earnings = sum((Decimal(str(trip.distance_km)) * profile.per_km_rate) if profile.per_km_rate else Decimal("0.00") for trip in trips)
        trip_earnings += sum((Decimal("1") * profile.per_trip_rate) for _ in trips)
        return trips, trip_earnings

    @staticmethod
    def _attendance_bonus(db: Session, driver_id: int, pay_period: PayPeriod):
        start = datetime(pay_period.year, pay_period.month, 1, tzinfo=timezone.utc)
        if pay_period.month == 12:
            end = datetime(pay_period.year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            end = datetime(pay_period.year, pay_period.month + 1, 1, tzinfo=timezone.utc)
        attendances = db.query(DriverAttendance).filter(DriverAttendance.driver_id == driver_id, DriverAttendance.date >= start, DriverAttendance.date < end).all()
        overtime = sum((Decimal("0.00")) for _ in attendances)
        return overtime

    @staticmethod
    def calculate_pay_period_records(db: Session, pay_period_id: int, user_id: int) -> list[PayrollRecord]:
        pay_period = db.get(PayPeriod, pay_period_id)
        if pay_period is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pay period not found")
        records: list[PayrollRecord] = []
        for driver in db.query(Driver).all():
            profile = db.query(DriverPayProfile).filter(DriverPayProfile.driver_id == driver.id).order_by(DriverPayProfile.effective_from.desc()).first()
            if profile is None:
                continue
            trips, trip_earnings = PayrollService._trip_amount_for_driver(db, driver.id, pay_period)
            adjustments = db.query(DriverAdjustment).filter(DriverAdjustment.driver_id == driver.id, DriverAdjustment.date >= datetime(pay_period.year, pay_period.month, 1, tzinfo=timezone.utc), DriverAdjustment.date < datetime(pay_period.year + (1 if pay_period.month == 12 else 0), 1 if pay_period.month == 12 else pay_period.month + 1, 1, tzinfo=timezone.utc)).all()
            bonus_total = sum((Decimal(str(adj.amount)) for adj in adjustments if adj.type == "BONUS"), Decimal("0.00"))
            allowances_total = sum((Decimal(str(adj.amount)) for adj in adjustments if adj.type == "ALLOWANCE"), Decimal("0.00"))
            penalty_total = sum((Decimal(str(adj.amount)) for adj in adjustments if adj.type in {"PENALTY", "DEDUCTION"}), Decimal("0.00"))
            advance_total = sum((Decimal(str(adv.monthly_recovery)) for adv in db.query(DriverAdvance).filter(DriverAdvance.driver_id == driver.id).all()), Decimal("0.00"))
            base = profile.base_salary
            overtime = Decimal("0.00")
            other_deduction = Decimal("0.00")
            gross = base + trip_earnings + Decimal("0.00") + overtime + bonus_total + allowances_total
            net = gross - advance_total - penalty_total - other_deduction
            record = db.query(PayrollRecord).filter(PayrollRecord.driver_id == driver.id, PayrollRecord.pay_period_id == pay_period.id).first()
            before = PayrollService._snapshot(record)
            if record is None:
                record = PayrollRecord(driver_id=driver.id, pay_period_id=pay_period.id)
            record.base_amount = base
            record.trip_earnings = trip_earnings
            record.distance_earnings = Decimal("0.00")
            record.overtime_amount = overtime
            record.bonus = bonus_total
            record.allowances = allowances_total
            record.advance_deduction = advance_total
            record.penalty_deduction = penalty_total
            record.other_deduction = other_deduction
            record.gross = gross
            record.net = net
            record.status = "DRAFT"
            db.add(record)
            db.commit()
            db.refresh(record)
            after = PayrollService._snapshot(record)
            PayrollService._audit(db, user_id, "CALCULATED", "payroll_record", record.id, before, after)
            records.append(record)
        pay_period.status = "CALCULATED"
        db.commit()
        return records

    @staticmethod
    def approve_payroll(db: Session, payroll_id: int, user_id: int, notes: str | None = None) -> PayrollRecord:
        record = db.get(PayrollRecord, payroll_id)
        if record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payroll record not found")
        if record.status == "PAID":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Paid payroll records cannot be modified")
        last_calculation = db.query(AuditLog).filter(AuditLog.entity == "payroll_record", AuditLog.entity_id == payroll_id, AuditLog.action == "CALCULATED").order_by(AuditLog.created_at.desc()).first()
        if last_calculation and last_calculation.user_id == user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Payroll calculator cannot approve the same payroll")
        before = PayrollService._snapshot(record)
        record.status = "APPROVED"
        record.approved_by = user_id
        record.notes = notes or record.notes
        db.commit()
        db.refresh(record)
        after = PayrollService._snapshot(record)
        PayrollService._audit(db, user_id, "APPROVED", "payroll_record", record.id, before, after)
        return record

    @staticmethod
    def mark_paid(db: Session, payroll_id: int, user_id: int, method: str, reference: str | None, paid_at: str | None) -> PayrollRecord:
        record = db.get(PayrollRecord, payroll_id)
        if record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payroll record not found")
        if record.status == "PAID":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payroll already paid")
        if record.status != "APPROVED":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only approved payroll records can be marked paid")
        before = PayrollService._snapshot(record)
        record.status = "PAID"
        record.payment_method = method
        record.payment_reference = reference
        record.paid_at = datetime.fromisoformat(paid_at) if paid_at else datetime.now(timezone.utc)
        db.commit()
        db.refresh(record)
        after = PayrollService._snapshot(record)
        PayrollService._audit(db, user_id, "PAID", "payroll_record", record.id, before, after)
        return record

    @staticmethod
    def payroll_summary(db: Session, month: int | None = None, year: int | None = None) -> dict[str, Any]:
        if month is None:
            month = datetime.now(timezone.utc).month
        if year is None:
            year = datetime.now(timezone.utc).year
        records = db.query(PayrollRecord).join(PayPeriod).filter(PayPeriod.month == month, PayPeriod.year == year).all()
        return {
            "month": month,
            "year": year,
            "total_drivers": len({record.driver_id for record in records}),
            "gross_total": sum((record.gross for record in records), Decimal("0.00")),
            "net_total": sum((record.net for record in records), Decimal("0.00")),
            "records": [PayrollService._snapshot(record) for record in records],
        }

    @staticmethod
    def export_payroll(db: Session, format: str = "csv") -> str:
        records = db.query(PayrollRecord).all()
        if format.lower() != "csv":
            return json.dumps([PayrollService._snapshot(record) for record in records], default=str)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["driver_id", "pay_period_id", "gross", "net", "status"]) 
        for record in records:
            writer.writerow([record.driver_id, record.pay_period_id, str(record.gross), str(record.net), record.status])
        return output.getvalue()

    @staticmethod
    def get_payslip_download(db: Session, payroll_id: int):
        record = db.get(PayrollRecord, payroll_id)
        if record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payroll record not found")
        driver = db.get(Driver, record.driver_id)
        pay_period = db.get(PayPeriod, record.pay_period_id)
        pdf_bytes = generate_payslip_pdf(record, driver, pay_period)
        payslip = db.query(Payslip).filter(Payslip.payroll_record_id == payroll_id).first()
        if payslip is None:
            payslip = Payslip(payroll_record_id=payroll_id, pdf_url="", generated_at=datetime.now(timezone.utc))
            db.add(payslip)
            db.commit()
        return {
            "filename": f"payslip_{payroll_id}.pdf",
            "content_type": "application/pdf",
            "content": pdf_bytes,
        }

    @staticmethod
    def driver_earnings_summary(db: Session, driver_id: int, month: int | None = None, year: int | None = None) -> dict[str, Any]:
        if month is None:
            month = datetime.now(timezone.utc).month
        if year is None:
            year = datetime.now(timezone.utc).year
        pay_period = db.query(PayPeriod).filter(PayPeriod.month == month, PayPeriod.year == year).first()
        if pay_period is None:
            return {"month": month, "year": year, "gross": "0.00", "net": "0.00", "records": []}
        record = db.query(PayrollRecord).filter(PayrollRecord.driver_id == driver_id, PayrollRecord.pay_period_id == pay_period.id).first()
        if record is None:
            return {"month": month, "year": year, "gross": "0.00", "net": "0.00", "records": []}
        return {"month": month, "year": year, "gross": str(record.gross), "net": str(record.net), "records": [PayrollService._snapshot(record)]}

    @staticmethod
    def masked_profile_response(profile: DriverPayProfile | None):
        if profile is None:
            return None
        masked = None
        if profile.bank_account_no_encrypted:
            try:
                masked = mask_value(decrypt_text(profile.bank_account_no_encrypted))
            except Exception:
                masked = "********"
        return {
            "id": profile.id,
            "driver_id": profile.driver_id,
            "pay_type": profile.pay_type,
            "base_salary": str(profile.base_salary),
            "per_trip_rate": str(profile.per_trip_rate),
            "per_km_rate": str(profile.per_km_rate),
            "overtime_rate": str(profile.overtime_rate),
            "bank_name": profile.bank_name,
            "bank_account_no": masked,
            "effective_from": profile.effective_from.isoformat(),
            "effective_to": profile.effective_to.isoformat() if profile.effective_to else None,
        }
