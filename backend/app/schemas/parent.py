from pydantic import BaseModel, ConfigDict, Field, EmailStr


class ParentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    phone: str
    email: str
    role: str = "PARENT"


class ParentStudentLink(BaseModel):
    parent_id: int
    student_id: int


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=8, max_length=32)
    email: EmailStr
