from datetime import datetime

from pydantic import BaseModel


class ExpenseOut(BaseModel):
    id: int
    item: str
    amount: float
    occurred_at: datetime

    class Config:
        from_attributes = True