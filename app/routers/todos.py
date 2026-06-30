from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.models.todo import Todo
from app.schemas.todo import TodoOut
from app.routers.input import TEMP_USER_ID

router = APIRouter(prefix="/todos", tags=["todos"])


@router.get("", response_model=list[TodoOut])
def list_todos(db: Session = Depends(get_db)):
    return db.query(Todo).filter(Todo.user_id == TEMP_USER_ID).order_by(Todo.created_at.desc()).all()