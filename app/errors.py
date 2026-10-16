import logging

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

LOGGER = logging.getLogger("calendar.errors")

FALLBACK = "Something went wrong. Please try again."

DB_DOWN = "The calendar database is not responding. Please try again in a moment."

SERVER_ERROR = "The server could not complete that request. Please try again."

# Each field keeps the name the screen shows, so a message points at the right box.
FIELD_NAMES = {
    "title": "Title",
    "event_type": "Event type",
    "company": "Company",
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
    "opportunity_type": "Opportunity type",
    "courses": "Course",
    "batches": "Batch",
    "departments": "Department",
    "remind_before": "Remind me",
    "linked_job": "Linked job",
    "url": "Job link",
    "reason": "Reason",
    "token": "Device token",
    "platform": "Platform",
    "change_reason": "Reason for change",
    "event_reminder_days_before": "Event Reminder: days before",
    "event_reminder_hours_before": "Event Reminder: hours before",
    "deadline_reminder_days_before": "Deadline Reminder: days before",
    "deadline_reminder_same_day": "Deadline Reminder: same day",
    "daily_nudge_limit": "Daily nudge limit per student",
    "quiet_hours_start": "Quiet hours start",
    "quiet_hours_end": "Quiet hours end",
}

# A model-level rule reports the whole model, so the field is read back from the message.
MODEL_FIELD_HINTS = (
    ("Unknown event type", "event_type"),
    ("Start and end time are required", "start_time"),
    ("End must be after the start", "end_time"),
    ("Mode is required", "mode"),
    ("Venue is required", "venue"),
    ("Online platform is required", "online_platform"),
    ("Course, batch and department are required", "courses"),
    ("Enter a valid link", "url"),
    ("Job title is required", "linked_job"),
    ("A short explanation is required", "note"),
    ("Quiet hours must start and end", "quiet_hours_start"),
)


def field_hint(message: str) -> str:
    return next((field for text, field in MODEL_FIELD_HINTS if message.startswith(text)), "")


# A short code beside the status, so the client can branch without reading the message.
CODES = {
    status.HTTP_400_BAD_REQUEST: "bad_request",
    status.HTTP_401_UNAUTHORIZED: "unauthenticated",
    status.HTTP_403_FORBIDDEN: "forbidden",
    status.HTTP_404_NOT_FOUND: "not_found",
    status.HTTP_409_CONFLICT: "conflict",
    status.HTTP_422_UNPROCESSABLE_ENTITY: "validation_error",
}


def field_of(location: tuple) -> str:
    parts = [str(part) for part in location if part not in ("body", "query", "path")]

    return parts[-1] if parts else ""


def field_label(location: tuple) -> str:
    name = field_of(location)
    if not name:
        return "This form"

    return FIELD_NAMES.get(name, name.replace("_", " ").capitalize())


def readable(error: dict) -> str:
    message = str(error.get("msg", "")).replace("Value error, ", "").strip()
    kind = error.get("type", "")
    label = field_label(tuple(error.get("loc", ())))

    if kind == "missing":
        return f"{label} is required"

    if kind.startswith(("string_too_long", "too_long")):
        return f"{label} is too long"

    if kind in ("less_than_equal", "greater_than_equal", "less_than", "greater_than"):
        limits = error.get("ctx", {})
        edge = limits.get("le", limits.get("ge", limits.get("lt", limits.get("gt"))))
        word = "or less" if kind.startswith("less") else "or more"

        return f"{label} must be {edge} {word}"

    if kind in ("literal_error", "enum"):
        return f"{label} has an unexpected value"

    if kind.endswith(("_parsing", "_type")):
        return f"{label} is not valid"

    return message or FALLBACK


# Every error answers in one shape: a one-line detail, a code, and the field when there is one.
def problem(
    code: str,
    detail: str,
    http_status: int,
    field: str = "",
    errors: list[dict] | None = None,
) -> JSONResponse:
    body: dict = {"detail": detail, "code": code}
    if field:
        body["field"] = field
    if errors:
        body["errors"] = errors

    return JSONResponse(status_code=http_status, content=body)


def register_errors(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def on_invalid_request(_: Request, error: RequestValidationError) -> JSONResponse:
        found = error.errors()
        if not found:
            return problem("validation_error", FALLBACK, status.HTTP_422_UNPROCESSABLE_ENTITY)

        every = []
        for entry in found:
            message = readable(entry)
            field = field_of(tuple(entry.get("loc", ()))) or field_hint(message)
            every.append({"field": field, "message": message})

        return problem(
            "validation_error",
            every[0]["message"],
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            field=every[0]["field"],
            errors=every,
        )

    @app.exception_handler(HTTPException)
    async def on_http_error(_: Request, error: HTTPException) -> JSONResponse:
        detail = error.detail if isinstance(error.detail, str) else FALLBACK

        return problem(CODES.get(error.status_code, "error"), detail, error.status_code)

    @app.exception_handler(SQLAlchemyError)
    async def on_db_error(_: Request, error: SQLAlchemyError) -> JSONResponse:
        LOGGER.exception("database call failed", exc_info=error)

        return problem("database_unavailable", DB_DOWN, status.HTTP_503_SERVICE_UNAVAILABLE)

    @app.exception_handler(Exception)
    async def on_unexpected(_: Request, error: Exception) -> JSONResponse:
        LOGGER.exception("unhandled request error", exc_info=error)

        return problem("server_error", SERVER_ERROR, status.HTTP_500_INTERNAL_SERVER_ERROR)
