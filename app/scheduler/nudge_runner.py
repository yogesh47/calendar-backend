import asyncio
import contextlib
import logging

from fastapi import FastAPI

from app.conf import DEFAULT_ORG_ID, NUDGE_TICK_SECONDS
from app.db.session import SessionLocal
from app.services import live_stream, nudges

LOGGER = logging.getLogger("nudges")

TASK_KEY = "nudge_task"


# One tick: schedule whatever is new, send whatever has fallen due.
def run_tick() -> dict[str, int]:
    with SessionLocal() as db:
        nudges.schedule_deadlines(db, DEFAULT_ORG_ID)
        counts = nudges.run_due(db)

    if counts["sent"]:
        live_stream.publish(DEFAULT_ORG_ID, "nudges")

    return counts


# The loop itself — never dies, just logs and waits for the next tick.
# The tick talks to the database, which blocks, so it runs in a worker thread:
# inside the event loop a slow or missing database would freeze every request.
async def nudge_loop() -> None:
    while True:
        try:
            await asyncio.to_thread(run_tick)
        except Exception:
            LOGGER.exception("nudge tick failed")

        await asyncio.sleep(NUDGE_TICK_SECONDS)


# Starts the loop when the API boots.
def start_nudge_runner(app: FastAPI) -> None:
    setattr(app.state, TASK_KEY, asyncio.create_task(nudge_loop()))


# Stops it cleanly when the API shuts down.
async def stop_nudge_runner(app: FastAPI) -> None:
    task = getattr(app.state, TASK_KEY, None)
    if not task:
        return

    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task
