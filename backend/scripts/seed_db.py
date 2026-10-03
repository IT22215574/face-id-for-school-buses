from datetime import datetime, timezone

from app.core.security import hash_api_key, hash_password
from app.db.init_db import create_all_tables
from app.db.session import SessionLocal
from app.models.bus import Bus
from app.models.bus_location import BusLocation
from app.models.device import Device
from app.models.emergency import EmergencyContact
from app.models.event import Event, EventType
from app.models.parent import Parent
from app.models.parent_student import ParentStudent
from app.models.payroll import Driver, DriverAttendance, DriverPayProfile, PayPeriod, Trip
from app.models.student import Student


def seed() -> None:
    db = SessionLocal()
    create_all_tables()

    admin = db.query(Parent).filter(Parent.email == "admin@example.com").first()
    if not admin:
        admin = Parent(
            name="System Admin",
            phone="+15550000000",
            email="admin@example.com",
            password_hash=hash_password("admin123"),
            role="ADMIN",
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)

    coordinator = db.query(Parent).filter(Parent.email == "coordinator@example.com").first()
    if not coordinator:
        coordinator = Parent(
            name="School Coordinator",
            phone="+15550000001",
            email="coordinator@example.com",
            password_hash=hash_password("coord123"),
            role="COORDINATOR",
        )
        db.add(coordinator)
        db.commit()
        db.refresh(coordinator)

    parent = db.query(Parent).filter(Parent.email == "parent@example.com").first()
    if not parent:
        parent = Parent(
            name="Jane Parent",
            phone="+15550001111",
            email="parent@example.com",
            password_hash=hash_password("password123"),
            fcm_token="demo-fcm-token",
            role="PARENT",
        )
        db.add(parent)
        db.commit()
        db.refresh(parent)

    driver_user = db.query(Parent).filter(Parent.email == "driver@example.com").first()
    if not driver_user:
        driver_user = Parent(
            name="Sam Driver",
            phone="+15550001112",
            email="driver@example.com",
            password_hash=hash_password("driver123"),
            role="DRIVER",
        )
        db.add(driver_user)
        db.commit()
        db.refresh(driver_user)

    student = db.query(Student).filter(Student.name == "Aisha").first()
    if not student:
        student = Student(name="Aisha", grade="5", school_id="SCH-001")
        db.add(student)
        db.commit()
        db.refresh(student)

    link = db.query(ParentStudent).filter_by(parent_id=parent.id, student_id=student.id).first()
    if not link:
        db.add(ParentStudent(parent_id=parent.id, student_id=student.id))
        db.commit()

    bus = db.query(Bus).filter(Bus.plate_no == "BUS-24").first()
    if not bus:
        bus = Bus(plate_no="BUS-24", device_id="BUS24-DEVICE-001", route_name="North Loop")
        db.add(bus)
        db.commit()
        db.refresh(bus)

    device = db.query(Device).filter(Device.bus_id == bus.id).first()
    if not device:
        device = Device(bus_id=bus.id, api_key_hash=hash_api_key("demo-device-key"), status="ACTIVE")
        db.add(device)
        db.commit()

    if not db.query(EmergencyContact).filter(EmergencyContact.name == "School Safety Desk").first():
        db.add(EmergencyContact(school_id="SCH-001", name="School Safety Desk", phone="+15550009999", role="COORDINATOR", priority_order=1))
        db.add(EmergencyContact(school_id="SCH-001", name="Transport Manager", phone="+15550009998", role="COORDINATOR", priority_order=2))

    location = db.query(BusLocation).filter(BusLocation.bus_id == bus.id).order_by(BusLocation.server_time.desc()).first()
    if not location:
        db.add(
            BusLocation(
                bus_id=bus.id,
                lat=6.9271,
                lng=79.8612,
                speed=25.0,
                heading=90.0,
                gps_time=datetime.now(timezone.utc),
                server_time=datetime.now(timezone.utc),
            )
        )

    existing_event = db.query(Event).filter_by(student_id=student.id, bus_id=bus.id).first()
    if not existing_event:
        db.add(
            Event(
                student_id=student.id,
                bus_id=bus.id,
                event_type=EventType.BOARDED,
                event_time=datetime.now(timezone.utc),
                lat=6.9271,
                lng=79.8612,
                confidence=0.99,
                source="DEVICE",
            )
        )

    driver = db.query(Driver).filter(Driver.user_id == driver_user.id).first()
    if not driver:
        driver = Driver(
            user_id=driver_user.id,
            name="Sam Driver",
            phone=driver_user.phone,
            license_no="DL-112233",
            nic="200012345V",
            bus_id=bus.id,
            status="ACTIVE",
        )
        db.add(driver)
        db.commit()
        db.refresh(driver)

    if not db.query(DriverPayProfile).filter(DriverPayProfile.driver_id == driver.id).first():
        db.add(
            DriverPayProfile(
                driver_id=driver.id,
                pay_type="MONTHLY_SALARY",
                base_salary=80000,
                per_trip_rate=1200,
                per_km_rate=150,
                overtime_rate=250,
                bank_name="People's Bank",
                bank_account_no_encrypted="",
            )
        )

    if not db.query(PayPeriod).filter(PayPeriod.month == datetime.now(timezone.utc).month, PayPeriod.year == datetime.now(timezone.utc).year).first():
        db.add(PayPeriod(month=datetime.now(timezone.utc).month, year=datetime.now(timezone.utc).year, status="OPEN"))

    if not db.query(Trip).filter(Trip.driver_id == driver.id).first():
        start = datetime.now(timezone.utc).replace(day=1, hour=7, minute=0, second=0, microsecond=0)
        db.add(
            Trip(
                bus_id=bus.id,
                driver_id=driver.id,
                route_name="North Loop",
                shift="MORNING",
                start_time=start,
                end_time=start.replace(hour=9),
                distance_km=42.5,
                status="COMPLETED",
            )
        )

    if not db.query(DriverAttendance).filter(DriverAttendance.driver_id == driver.id).first():
        day = datetime.now(timezone.utc).replace(day=1, hour=8, minute=0, second=0, microsecond=0)
        db.add(
            DriverAttendance(
                driver_id=driver.id,
                date=day,
                check_in=day.replace(hour=6, minute=30),
                check_out=day.replace(hour=15, minute=15),
                status="PRESENT",
            )
        )

    db.commit()
    print("Seed data created successfully")


if __name__ == "__main__":
    seed()
