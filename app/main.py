from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.conf import CORS_ORIGINS
from app.errors import register_errors
from app.routes import auth, calendar, health, settings
from app.scheduler import start_nudge_runner, stop_nudge_runner

app = FastAPI(title="Campus Calendar", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_errors(app)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(calendar.router)
app.include_router(settings.router)


@app.on_event("startup")
async def on_startup() -> None:
    start_nudge_runner(app)


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await stop_nudge_runner(app)
