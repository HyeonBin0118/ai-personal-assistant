from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.models.expense import Expense
from app.schemas.expense import ExpenseOut
from app.routers.input import TEMP_USER_ID

router = APIRouter(prefix="/expenses", tags=["expenses"])


@router.get("", response_model=list[ExpenseOut])
def list_expenses(db: Session = Depends(get_db)):
    return db.query(Expense).filter(Expense.user_id == TEMP_USER_ID).order_by(Expense.occurred_at.desc()).all()