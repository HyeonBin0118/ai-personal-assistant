import enum

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector

from app.database import Base


class ScheduleStatus(str, enum.Enum):
    pending = "pending"
    completed = "completed"
    cancelled = "cancelled"


class Schedule(Base):
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    start_at = Column(DateTime(timezone=True), nullable=False)
    notify_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(Enum(ScheduleStatus), default=ScheduleStatus.pending, nullable=False)
    embedding = Column(Vector(1536), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())