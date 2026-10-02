from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EventCreate(BaseModel):
    student_id: int
    bus_id: int
    event_type: str
    event_time: datetime
    lat: float
    lng: float
    confidence: float | None = None
    source: str = "DEVICE"


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    bus_id: int
    event_type: str
    event_time: datetime
    lat: float
    lng: float
    confidence: float | None = None
    source: str


class EventTimelineOut(BaseModel):
    student_id: int
    events: list[EventOut]
