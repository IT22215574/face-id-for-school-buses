from fastapi import HTTPException
from app.models.parent_student import ParentStudent
from app.models.student_transport import StudentTransport
from app.models.payroll import Driver

# Approximate stops for demonstration; these are not road navigation geometry.
SCHOOLS = {
    "KUR-MALIYADEVA": {"name": "Maliyadeva College, Kurunegala", "lat": 7.4863, "lng": 80.3548},
    "KUR-MALIYADEVA-BALIKA": {"name": "Maliyadeva Balika Vidyalaya, Kurunegala", "lat": 7.4787, "lng": 80.3609},
}
ROUTE = [
    {"name": "Kurunegala town pickup", "lat": 7.4863, "lng": 80.3647},
    {"name": "Negombo Road", "lat": 7.4870, "lng": 80.3590},
    SCHOOLS["KUR-MALIYADEVA"],
    SCHOOLS["KUR-MALIYADEVA-BALIKA"],
]


def authorize_bus(db, user, bus_id):
    if user.role in {"ADMIN", "COORDINATOR"}:
        return
    if user.role == "DRIVER" and db.query(Driver).filter_by(user_id=user.id, bus_id=bus_id, status="ACTIVE").first():
        return
    if user.role == "PARENT" and db.query(StudentTransport).join(
        ParentStudent, ParentStudent.student_id == StudentTransport.student_id
    ).filter(ParentStudent.parent_id == user.id, StudentTransport.bus_id == bus_id).first():
        return
    raise HTTPException(status_code=403, detail="Bus is not assigned to your account")
