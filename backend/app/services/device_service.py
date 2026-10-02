from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import hash_api_key
from app.models.device import Device
from app.models.bus_location import BusLocation
from app.models.event import Event, EventType


def validate_device_api_key(db: Session, api_key: str) -> Device:
    hashed = hash_api_key(api_key)
    device = db.query(Device).filter(Device.api_key_hash == hashed).first()
    if device is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid device API key")
    if device.status != "ACTIVE":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Device inactive")
    device.last_seen_at = datetime.now(timezone.utc)
    db.commit()
    return device


def save_bus_location(db: Session, bus_id: int, lat: float, lng: float, speed: float | None, heading: float | None, gps_time: datetime | None) -> BusLocation:
    location = BusLocation(
        bus_id=bus_id,
        lat=lat,
        lng=lng,
        speed=speed,
        heading=heading,
        gps_time=gps_time,
        server_time=datetime.now(timezone.utc),
    )
    db.add(location)
    db.commit()
    db.refresh(location)
    return location


def save_event(db: Session, student_id: int, bus_id: int, event_type: str, event_time: datetime, lat: float, lng: float, confidence: float | None, source: str) -> Event:
    normalized = EventType[event_type.upper()] if event_type.upper() in EventType.__members__ else EventType.BOARDED
    event = Event(
        student_id=student_id,
        bus_id=bus_id,
        event_type=normalized,
        event_time=event_time,
        lat=lat,
        lng=lng,
        confidence=confidence,
        source=source,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event
