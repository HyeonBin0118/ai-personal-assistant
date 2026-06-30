from datetime import datetime

from pydantic import BaseModel


class TodoOut(BaseModel):
    id: int
    content: str
    is_done: bool
    created_at: datetime

    class Config:
        from_attributes = True