from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DeviceCreate(BaseModel):
    bus_id: int
    api_key: str = Field(..., min_length=16, max_length=255)
    status: str = "ACTIVE"


class DeviceEventIn(BaseModel):
    student_id: int
    bus_id: int
    event_type: str
    event_time: datetime
    lat: float
    lng: float
    confidence: float | None = None


class DeviceLocationIn(BaseModel):
    bus_id: int
    lat: float
    lng: float
    speed: float | None = None
    heading: float | None = None
    gps_time: datetime | None = None


class DeviceHeartbeat(BaseModel):
    bus_id: int
    status: str = "ACTIVE"


class DeviceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    bus_id: int
    status: str
    last_seen_at: datetime | None = None
