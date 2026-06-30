from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.schemas.input import InputRequest, InputResponse
from app.services.llm_classifier import classify
from app.models.schedule import Schedule
from app.models.expense import Expense
from app.models.todo import Todo

router = APIRouter(prefix="/input", tags=["input"])

# Phase 2에서 JWT 인증 붙기 전까지 임시 고정 사용자 사용
TEMP_USER_ID = 1


@router.post("", response_model=InputResponse)
def create_input(payload: InputRequest, db: Session = Depends(get_db)):
    result = classify(payload.text)

    if result.category == "schedule":
        if not result.title or not result.start_at:
            raise HTTPException(status_code=422, detail="일정 분류 결과에 제목 또는 시각이 없음")
        record = Schedule(
            user_id=TEMP_USER_ID,
            title=result.title,
            start_at=result.start_at,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return InputResponse(category="schedule", saved_id=record.id, message=f"일정 등록: {record.title}")

    elif result.category == "expense":
        if result.amount is None or not result.item:
            raise HTTPException(status_code=422, detail="지출 분류 결과에 금액 또는 항목이 없음")
        record = Expense(
            user_id=TEMP_USER_ID,
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
            user_id=TEMP_USER_ID,
            content=result.content,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return InputResponse(category="todo", saved_id=record.id, message=f"투두 등록: {record.content}")