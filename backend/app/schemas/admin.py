from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ParentCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    phone: str = Field(..., min_length=8, max_length=32)
    email: EmailStr
    password_hash: str = Field(..., min_length=8, max_length=255)


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


class ParentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    phone: str
    email: str
    role: str = "PARENT"


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
