from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user
from app.schemas.input import InputRequest, InputResponse
from app.services.llm_classifier import classify
from app.models.schedule import Schedule
from app.models.expense import Expense
from app.models.todo import Todo
from app.models.user import User

router = APIRouter(prefix="/input", tags=["input"])


@router.post("", response_model=InputResponse)
def create_input(
    payload: InputRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = classify(payload.text, db=db)

    if result.category == "schedule":
        if not result.title or not result.start_at:
            raise HTTPException(status_code=422, detail="일정 분류 결과에 제목 또는 시각이 없음")
        record = Schedule(
            user_id=current_user.id,
            title=result.title,
            start_at=result.start_at,
            notify_at=result.notify_at,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        msg = f"일정 등록: {record.title}"
        if record.notify_at:
            msg += f" ({record.notify_at.strftime('%m월 %d일 %H:%M')}에 알림)"
        return InputResponse(category="schedule", saved_id=record.id, message=msg)

    elif result.category == "expense":
        if result.amount is None or not result.item:
            raise HTTPException(status_code=422, detail="지출 분류 결과에 금액 또는 항목이 없음")
        record = Expense(
            user_id=current_user.id,
            item=result.item,
            amount=result.amount,
            occurred_at=datetime.now(),
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return InputResponse(category="expense", saved_id=record.id, message=f"지출 등록: {record.item} {record.amount}원")

    else:
        if not result.content:
            raise HTTPException(status_code=422, detail="투두 분류 결과에 내용이 없음")
        record = Todo(
            user_id=current_user.id,
            content=result.content,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return InputResponse(category="todo", saved_id=record.id, message=f"투두 등록: {record.content}")