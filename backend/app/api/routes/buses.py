from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_parent
from app.models.bus import Bus
from app.models.bus_location import BusLocation
from app.services.bus_service import get_live_location, get_route_history

router = APIRouter(tags=["Buses"])


@router.get("/buses/{bus_id}/live-location")
def read_bus_live_location(bus_id: int, current_parent=Depends(require_parent), db: Session = Depends(get_db)):
    bus = db.get(Bus, bus_id)
    if bus is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bus not found")
    location = get_live_location(db, bus_id)
    if location is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No live location available")
    return location


@router.get("/buses/{bus_id}/route-history")
def read_route_history(
    bus_id: int,
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = None,
    current_parent=Depends(require_parent),
    db: Session = Depends(get_db),
):
    bus = db.get(Bus, bus_id)
    if bus is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bus not found")
    points = get_route_history(db, bus_id, from_, to)
    return {"bus_id": bus_id, "points": points}
