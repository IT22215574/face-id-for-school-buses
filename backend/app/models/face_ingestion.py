"""Hardware-independent durable integration records. Timestamps are UTC."""
from datetime import datetime
from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class FaceEnrollment(Base):
    __tablename__ = 'face_enrollments'
    __table_args__ = (UniqueConstraint('device_id', 'terminal_user_id', 'effective_from'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey('face_terminals.id'), index=True)
    terminal_user_id: Mapped[str] = mapped_column(String(32))
    student_id: Mapped[int] = mapped_column(ForeignKey('students.id'))
    effective_from: Mapped[datetime]
    effective_until: Mapped[datetime | None]
    consent_reference: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


class FaceDirection(Base):
    __tablename__ = 'face_directions'
    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey('face_terminals.id'), index=True)
    event_type: Mapped[str] = mapped_column(String(10))
    effective_from: Mapped[datetime]
    effective_until: Mapped[datetime | None]
    actor_id: Mapped[int] = mapped_column(ForeignKey('parents.id'))


class FaceInbox(Base):
    __tablename__ = 'face_inbox'
    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey('face_terminals.id'), index=True)
    deduplication_key: Mapped[str] = mapped_column(String(64), unique=True)
    raw_payload: Mapped[str | None] = mapped_column(Text)  # Fernet encrypted; purged by worker
    terminal_user_id: Mapped[str] = mapped_column(String(32))
    device_event_time: Mapped[datetime | None]
    received_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    processing_status: Mapped[str] = mapped_column(String(30), default='RECEIVED', index=True)
    processing_error: Mapped[str | None] = mapped_column(String(200))
    event_id: Mapped[int | None] = mapped_column(ForeignKey('events.id'))
    duplicate_count: Mapped[int] = mapped_column(default=0)
    override_direction: Mapped[str | None] = mapped_column(String(10))
    override_actor_id: Mapped[int | None] = mapped_column(ForeignKey('parents.id'))
    override_reason: Mapped[str | None] = mapped_column(String(200))


class FaceNotificationJob(Base):
    __tablename__ = 'face_notification_jobs'
    __table_args__ = (UniqueConstraint('event_id', 'parent_id'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey('events.id'))
    parent_id: Mapped[int] = mapped_column(ForeignKey('parents.id'))
    status: Mapped[str] = mapped_column(String(20), default='PENDING')
    attempts: Mapped[int] = mapped_column(default=0)
    last_error: Mapped[str | None] = mapped_column(String(200))
    next_attempt_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
