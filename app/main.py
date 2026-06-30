from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

from app.routers import input as input_router
from app.routers import schedules, expenses, todos, auth, notifications
from app.services.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="AI Personal Assistant", lifespan=lifespan)


@app.get("/")
def root():
    return RedirectResponse(url="/static/login.html")


app.include_router(auth.router)
app.include_router(input_router.router)
app.include_router(schedules.router)
app.include_router(expenses.router)
app.include_router(todos.router)
app.include_router(notifications.router)

app.mount("/static", StaticFiles(directory="app/static"), name="static")