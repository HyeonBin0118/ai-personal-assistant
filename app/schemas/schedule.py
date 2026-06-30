from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.schedule import ScheduleStatus


class ScheduleOut(BaseModel):
    id: int
    title: str
    start_at: datetime
    notify_at: Optional[datetime]
    status: ScheduleStatus

    class Config:
        from_attributes = True