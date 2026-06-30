from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.models.schedule import Schedule
from app.schemas.schedule import ScheduleOut
from app.routers.input import TEMP_USER_ID

router = APIRouter(prefix="/schedules", tags=["schedules"])


@router.get("", response_model=list[ScheduleOut])
def list_schedules(db: Session = Depends(get_db)):
    return db.query(Schedule).filter(Schedule.user_id == TEMP_USER_ID).order_by(Schedule.start_at).all()