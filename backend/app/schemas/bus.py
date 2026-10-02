from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BusCreate(BaseModel):
    plate_no: str = Field(..., min_length=2, max_length=32)
    device_id: str = Field(..., min_length=2, max_length=64)
    route_name: str = Field(..., min_length=2, max_length=120)


class BusOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    plate_no: str
    device_id: str
    route_name: str
    created_at: datetime


class BusLocationCreate(BaseModel):
    bus_id: int
    lat: float
    lng: float
    speed: float | None = None
    heading: float | None = None
    gps_time: datetime | None = None


class BusLocationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    bus_id: int
    lat: float
    lng: float
    speed: float | None = None
    heading: float | None = None
    gps_time: datetime | None = None
    server_time: datetime


class RouteHistoryOut(BaseModel):
    bus_id: int
    points: list[BusLocationOut]
