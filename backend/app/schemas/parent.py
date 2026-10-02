from pydantic import BaseModel, ConfigDict, Field


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
