from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_parent
from app.models.parent import Parent
from app.models.student import Student
from app.schemas.parent import ParentOut
from app.schemas.student import StudentOut

router = APIRouter(tags=["Parents"])


@router.get("/me", response_model=ParentOut)
def read_me(current_parent: Parent = Depends(require_parent)):
    return current_parent


@router.get("/me/students", response_model=list[StudentOut])
def read_my_students(current_parent: Parent = Depends(require_parent), db: Session = Depends(get_db)):
    return current_parent.students
