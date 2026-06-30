from typing import Literal, Optional
from datetime import datetime

from pydantic import BaseModel


class InputRequest(BaseModel):
    text: str


class ClassificationResult(BaseModel):
    category: Literal["schedule", "expense", "todo"]
    title: Optional[str] = None
    start_at: Optional[datetime] = None
    amount: Optional[float] = None
    item: Optional[str] = None
    content: Optional[str] = None


class InputResponse(BaseModel):
    category: str
    saved_id: int
    message: str