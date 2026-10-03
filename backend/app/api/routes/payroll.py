from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_admin, require_admin_or_coordinator, require_parent
from app.core.encryption import mask_value
from app.models.emergency import EmergencyAlert
from app.models.parent import Parent
from app.models.payroll import Driver, DriverAdvance, DriverAdjustment, PayPeriod, PayrollRecord, Payslip
from app.services.payroll_service import PayrollService

router = APIRouter(tags=["Payroll"])


class PayProfileIn(BaseModel):
    pay_type: str = "MONTHLY_SALARY"
    base_salary: Decimal = Decimal("0.00")
    per_trip_rate: Decimal = Decimal("0.00")
    per_km_rate: Decimal = Decimal("0.00")
    overtime_rate: Decimal = Decimal("0.00")
    bank_name: str | None = None
    bank_account_no: str | None = None
    effective_from: str | None = None


class PayPeriodCreateIn(BaseModel):
    month: int = Field(..., ge=1, le=12)
    year: int = Field(..., ge=2000)


class PayrollApproveIn(BaseModel):
    notes: str | None = None


class AdvanceCreateIn(BaseModel):
    driver_id: int
    amount: Decimal
    reason: str
    issued_date: str | None = None
    monthly_recovery: Decimal = Decimal("0.00")


class AdjustmentCreateIn(BaseModel):
    driver_id: int
    type: str
    amount: Decimal
    reason: str
    date: str | None = None


class PayrollPaymentIn(BaseModel):
    payment_method: str = "BANK_TRANSFER"
    payment_reference: str | None = None
    paid_at: str | None = None


@router.get("/admin/drivers")
def admin_list_drivers(db: Session = Depends(get_db), current_user: Parent = Depends(require_admin_or_coordinator)):
    return db.query(Driver).order_by(Driver.created_at.desc()).all()


@router.get("/admin/drivers/{driver_id}")
def admin_get_driver(driver_id: int, db: Session = Depends(get_db), current_user: Parent = Depends(require_admin_or_coordinator)):
    driver = db.get(Driver, driver_id)
    if driver is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Driver not found")
    return driver


@router.post("/admin/drivers/{driver_id}/pay-profile")
def put_driver_pay_profile(driver_id: int, payload: PayProfileIn, db: Session = Depends(get_db), current_user: Parent = Depends(require_admin_or_coordinator)):
    return PayrollService.upsert_driver_pay_profile(db, driver_id, payload.model_dump())


@router.post("/admin/pay-periods", status_code=status.HTTP_201_CREATED)
def create_pay_period(payload: PayPeriodCreateIn, db: Session = Depends(get_db), current_user: Parent = Depends(require_admin_or_coordinator)):
    return PayrollService.create_pay_period(db, payload.month, payload.year)


@router.post("/admin/pay-periods/{pay_period_id}/calculate")
def calculate_pay_period(pay_period_id: int, db: Session = Depends(get_db), current_user: Parent = Depends(require_admin_or_coordinator)):
    return PayrollService.calculate_pay_period_records(db, pay_period_id, current_user.id)


@router.post("/admin/payroll/{payroll_id}/approve")
def approve_payroll(payroll_id: int, payload: PayrollApproveIn, db: Session = Depends(get_db), current_user: Parent = Depends(require_admin_or_coordinator)):
    return PayrollService.approve_payroll(db, payroll_id, current_user.id, payload.notes)


@router.post("/admin/payroll/{payroll_id}/mark-paid")
def mark_paid(payroll_id: int, payload: PayrollPaymentIn, db: Session = Depends(get_db), current_user: Parent = Depends(require_admin_or_coordinator)):
    return PayrollService.mark_paid(db, payroll_id, current_user.id, payload.payment_method, payload.payment_reference, payload.paid_at)


@router.post("/admin/advances", status_code=status.HTTP_201_CREATED)
def create_advance(payload: AdvanceCreateIn, db: Session = Depends(get_db), current_user: Parent = Depends(require_admin_or_coordinator)):
    return PayrollService.create_advance(db, payload.driver_id, payload.amount, payload.reason, payload.issued_date, payload.monthly_recovery)


@router.post("/admin/adjustments", status_code=status.HTTP_201_CREATED)
def create_adjustment(payload: AdjustmentCreateIn, db: Session = Depends(get_db), current_user: Parent = Depends(require_admin_or_coordinator)):
    return PayrollService.create_adjustment(db, payload.driver_id, payload.type, payload.amount, payload.reason, payload.date, current_user.id)


@router.get("/admin/payroll/summary")
def payroll_summary(month: int | None = Query(default=None), year: int | None = Query(default=None), db: Session = Depends(get_db), current_user: Parent = Depends(require_admin_or_coordinator)):
    return PayrollService.payroll_summary(db, month, year)


@router.get("/admin/payroll/export")
def export_payroll(format: str = "csv", db: Session = Depends(get_db), current_user: Parent = Depends(require_admin_or_coordinator)):
    return PayrollService.export_payroll(db, format=format)


@router.get("/admin/payroll/{payroll_id}/payslip.pdf")
def payslip_pdf(payroll_id: int, db: Session = Depends(get_db), current_user: Parent = Depends(require_admin_or_coordinator)):
    return PayrollService.get_payslip_download(db, payroll_id)


@router.get("/driver/me/earnings")
def driver_earnings(month: int | None = Query(default=None), year: int | None = Query(default=None), db: Session = Depends(get_db), current_user: Parent = Depends(require_parent)):
    driver = db.query(Driver).filter(Driver.user_id == current_user.id).first()
    if driver is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Driver profile not found")
    return PayrollService.driver_earnings_summary(db, driver.id, month, year)


@router.get("/driver/me/payslips")
def my_payslips(db: Session = Depends(get_db), current_user: Parent = Depends(require_parent)):
    driver = db.query(Driver).filter(Driver.user_id == current_user.id).first()
    if driver is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Driver profile not found")
    records = db.query(PayrollRecord).filter(PayrollRecord.driver_id == driver.id).all()
    return [{"id": rec.id, "status": rec.status, "net": float(rec.net), "gross": float(rec.gross), "period_id": rec.pay_period_id} for rec in records]


@router.get("/driver/me/payslips/{payslip_id}.pdf")
def my_payslip_pdf(payslip_id: int, db: Session = Depends(get_db), current_user: Parent = Depends(require_parent)):
    driver = db.query(Driver).filter(Driver.user_id == current_user.id).first()
    if driver is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Driver profile not found")
    record = db.query(PayrollRecord).filter(PayrollRecord.id == payslip_id, PayrollRecord.driver_id == driver.id).first()
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payslip not found")
    return PayrollService.get_payslip_download(db, payslip_id)


@router.get("/driver/me/trips")
def my_trips(db: Session = Depends(get_db), current_user: Parent = Depends(require_parent)):
    driver = db.query(Driver).filter(Driver.user_id == current_user.id).first()
    if driver is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Driver profile not found")
    return db.query(EmergencyAlert).filter_by(driver_id=driver.id).all() if False else []


@router.get("/driver/me/advances")
def my_advances(db: Session = Depends(get_db), current_user: Parent = Depends(require_parent)):
    driver = db.query(Driver).filter(Driver.user_id == current_user.id).first()
    if driver is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Driver profile not found")
    return db.query(DriverAdvance).filter(DriverAdvance.driver_id == driver.id).all()
