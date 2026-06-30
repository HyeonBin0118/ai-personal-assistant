from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.deps import get_db, get_current_user
from app.models.schedule import Schedule, ScheduleStatus
from app.models.user import User
from app.schemas.schedule import ScheduleOut

router = APIRouter(prefix="/schedules", tags=["schedules"])


class ScheduleStatusUpdate(BaseModel):
    status: ScheduleStatus


@router.get("", response_model=list[ScheduleOut])
def list_schedules(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Schedule).filter(Schedule.user_id == current_user.id).order_by(Schedule.start_at).all()


@router.patch("/{schedule_id}/status", response_model=ScheduleOut)
def update_schedule_status(
    schedule_id: int,
    payload: ScheduleStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    schedule = (
        db.query(Schedule)
        .filter(Schedule.id == schedule_id, Schedule.user_id == current_user.id)
        .first()
    )
    if not schedule:
        raise HTTPException(status_code=404, detail="일정을 찾을 수 없음")

    schedule.status = payload.status
    db.commit()
    db.refresh(schedule)
    return schedule