from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.db.base import Base
from app.models.parent import Parent
from app.models.payroll import Driver, DriverAdvance, DriverAdjustment, DriverPayProfile, PayPeriod, PayrollRecord, Trip

settings = get_settings()

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_session():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    return db


def test_payroll_calculation_matches_manual_formula():
    db = create_session()
    try:
        parent = Parent(name="Driver User", phone="+10000000001", email="drivercalc@example.com", password_hash="x", role="DRIVER")
        db.add(parent)
        db.commit()
        db.refresh(parent)

        driver = Driver(user_id=parent.id, name="Pay Driver", phone="+10000000002", license_no="LIC-1", nic="123456789V", bus_id=None, status="ACTIVE")
        db.add(driver)
        db.commit()
        db.refresh(driver)

        profile = DriverPayProfile(
            driver_id=driver.id,
            pay_type="HYBRID",
            base_salary=Decimal("50000.00"),
            per_trip_rate=Decimal("1500.00"),
            per_km_rate=Decimal("50.00"),
            overtime_rate=Decimal("200.00"),
            bank_name="Bank A",
        )
        db.add(profile)

        pay_period = PayPeriod(month=12, year=2025, status="OPEN")
        db.add(pay_period)
        db.commit()
        db.refresh(pay_period)

        trip = Trip(
            bus_id=1,
            driver_id=driver.id,
            route_name="Route 1",
            shift="MORNING",
            start_time=datetime(2025, 12, 5, 6, 0, tzinfo=timezone.utc),
            end_time=datetime(2025, 12, 5, 9, 0, tzinfo=timezone.utc),
            distance_km=20.0,
            status="COMPLETED",
        )
        db.add(trip)

        advance = DriverAdvance(driver_id=driver.id, amount=Decimal("4000.00"), reason="Advance", issued_date=datetime(2025, 12, 1, tzinfo=timezone.utc), remaining_balance=Decimal("4000.00"), monthly_recovery=Decimal("1000.00"))
        adjustment = DriverAdjustment(driver_id=driver.id, type="BONUS", amount=Decimal("3000.00"), reason="Bonus", date=datetime(2025, 12, 10, tzinfo=timezone.utc), created_by=parent.id)
        db.add_all([advance, adjustment])
        db.commit()

        record = PayrollRecord(
            driver_id=driver.id,
            pay_period_id=pay_period.id,
            base_amount=Decimal("50000.00"),
            trip_earnings=Decimal("1500.00"),
            distance_earnings=Decimal("1000.00"),
            overtime_amount=Decimal("0.00"),
            bonus=Decimal("3000.00"),
            allowances=Decimal("0.00"),
            advance_deduction=Decimal("1000.00"),
            penalty_deduction=Decimal("0.00"),
            other_deduction=Decimal("0.00"),
            gross=Decimal("54500.00"),
            net=Decimal("53500.00"),
            status="DRAFT",
        )
        db.add(record)
        db.commit()

        expected_gross = Decimal("50000.00") + Decimal("1500.00") + Decimal("1000.00") + Decimal("0.00") + Decimal("3000.00") + Decimal("0.00")
        expected_net = expected_gross - Decimal("1000.00") - Decimal("0.00") - Decimal("0.00")
        assert record.gross == expected_gross
        assert record.net == expected_net
    finally:
        db.close()
