from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

FALLBACK = "Something went wrong. Please try again."

FIELD_NAMES = {
    "title": "Title",
    "event_type": "Event type",
    "event_date": "Start date",
    "end_date": "End date",
    "start_time": "Start time",
    "end_time": "End time",
    "mode": "Mode",
    "venue": "Venue",
    "online_platform": "Online platform",
    "description": "Description",
    "note": "Note",
    "audience": "Audience",
    "reason": "Reason",
    "event_reminder_days_before": "Event Reminder: days before",
    "event_reminder_hours_before": "Event Reminder: hours before",
    "deadline_reminder_days_before": "Deadline Reminder: days before",
    "deadline_reminder_same_day": "Deadline Reminder: same day",
    "daily_nudge_limit": "Daily nudge limit per student",
    "quiet_hours_start": "Quiet hours start",
    "quiet_hours_end": "Quiet hours end",
}


def field_label(location: tuple) -> str:
    parts = [str(part) for part in location if part not in ("body", "query", "path")]
    if not parts:
        return "This form"

    return FIELD_NAMES.get(parts[-1], str(parts[-1]).replace("_", " ").capitalize())


def readable(error: dict) -> str:
    message = str(error.get("msg", "")).replace("Value error, ", "").strip()
    kind = error.get("type", "")

    if kind == "missing":
        return f"{field_label(tuple(error.get('loc', ())))} is required"

    if kind.startswith(("string_too_long", "too_long")):
        return f"{field_label(tuple(error.get('loc', ())))} is too long"

    if kind in ("less_than_equal", "greater_than_equal", "less_than", "greater_than"):
        limits = error.get("ctx", {})
        edge = limits.get("le", limits.get("ge", limits.get("lt", limits.get("gt"))))
        word = "or less" if kind.startswith("less") else "or more"

        return f"{field_label(tuple(error.get('loc', ())))} must be {edge} {word}"

    if kind in ("literal_error", "enum"):
        return f"{field_label(tuple(error.get('loc', ())))} has an unexpected value"

    if kind.endswith(("_parsing", "_type")):
        return f"{field_label(tuple(error.get('loc', ())))} is not valid"

    return message or FALLBACK


def register_errors(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def on_invalid_request(_: Request, error: RequestValidationError) -> JSONResponse:
        found = error.errors()

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": readable(found[0]) if found else FALLBACK},
        )

    @app.exception_handler(Exception)
    async def on_unexpected(_: Request, __: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "The server could not complete that request. Please try again."},
        )
