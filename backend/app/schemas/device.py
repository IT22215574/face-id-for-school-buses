from datetime import datetime
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, FiniteFloat


class DeviceCreate(BaseModel):
    bus_id: int
    api_key: str = Field(..., min_length=16, max_length=255)
    status: str = "ACTIVE"


class DeviceEventIn(BaseModel):
    student_id: int
    bus_id: int
    event_type: Literal["BOARDED", "ALIGHTED"]
    event_time: AwareDatetime
    lat: FiniteFloat = Field(ge=-90, le=90)
    lng: FiniteFloat = Field(ge=-180, le=180)
    confidence: FiniteFloat | None = Field(default=None, ge=0, le=1)


class DeviceLocationIn(BaseModel):
    accuracy_m: FiniteFloat | None = Field(default=None, ge=0)
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
