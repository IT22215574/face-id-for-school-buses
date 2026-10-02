from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.bus import Bus
from app.models.bus_location import BusLocation


def get_live_location(db: Session, bus_id: int) -> BusLocation | None:
    return db.query(BusLocation).filter(BusLocation.bus_id == bus_id).order_by(BusLocation.server_time.desc()).first()


def get_route_history(db: Session, bus_id: int, from_dt: datetime | None, to_dt: datetime | None) -> list[BusLocation]:
    query = db.query(BusLocation).filter(BusLocation.bus_id == bus_id)
    if from_dt:
        query = query.filter(BusLocation.server_time >= from_dt)
    if to_dt:
        query = query.filter(BusLocation.server_time <= to_dt)
    return query.order_by(BusLocation.server_time.asc()).all()


def ensure_bus_exists(db: Session, bus_id: int) -> Bus:
    bus = db.get(Bus, bus_id)
    if bus is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bus not found")
    return bus
