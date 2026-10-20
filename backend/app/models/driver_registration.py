from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class DriverRegistration(Base):
    __tablename__ = 'driver_registrations'
    driver_id: Mapped[int] = mapped_column(ForeignKey('drivers.id'), primary_key=True)
    # Identity documents and assistant personal information are encrypted at rest.
    encrypted_details: Mapped[str] = mapped_column(Text, nullable=False)
