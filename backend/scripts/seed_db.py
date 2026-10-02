from datetime import datetime, timezone

from app.core.security import hash_api_key, hash_password
from app.db.init_db import create_all_tables
from app.db.session import SessionLocal
from app.models.bus import Bus
from app.models.device import Device
from app.models.parent import Parent
from app.models.parent_student import ParentStudent
from app.models.student import Student
from app.models.bus_location import BusLocation
from app.models.event import Event, EventType


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

    db.commit()
    print("Seed data created successfully")


if __name__ == "__main__":
    seed()
