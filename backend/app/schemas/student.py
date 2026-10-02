from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class StudentCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    grade: str = Field(..., max_length=30)
    school_id: str = Field(..., min_length=1, max_length=80)


class StudentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    grade: str
    school_id: str
    created_at: datetime


class StudentStatusOut(BaseModel):
    student_id: int
    status: str
    last_event: str | None = None
    last_seen_at: datetime | None = None
