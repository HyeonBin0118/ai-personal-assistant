from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.database import Base, engine, SessionLocal
from app.models.user import User
from app.routers import input as input_router
from app.routers import schedules, expenses, todos


def _ensure_temp_user():
    """Phase 2에서 실제 인증이 들어가기 전까지 임시 고정 사용자를 보장."""
    db: Session = SessionLocal()
    try:
        existing = db.query(User).filter(User.id == 1).first()
        if not existing:
            temp_user = User(id=1, email="temp@local", hashed_password="placeholder")
            db.add(temp_user)
            db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    _ensure_temp_user()
    yield


app = FastAPI(title="AI Personal Assistant", lifespan=lifespan)

app.include_router(input_router.router)
app.include_router(schedules.router)
app.include_router(expenses.router)
app.include_router(todos.router)

app.mount("/static", StaticFiles(directory="app/static"), name="static")