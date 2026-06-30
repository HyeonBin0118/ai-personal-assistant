from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routers import input as input_router
from app.routers import schedules, expenses, todos, auth


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="AI Personal Assistant", lifespan=lifespan)

app.include_router(auth.router)
app.include_router(input_router.router)
app.include_router(schedules.router)
app.include_router(expenses.router)
app.include_router(todos.router)

app.mount("/static", StaticFiles(directory="app/static"), name="static")