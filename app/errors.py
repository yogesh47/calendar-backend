import logging

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.exceptions import (
    AlreadyExistError,
    AuthenticationError,
    InvalidInputError,
    NotExistError,
    PermissionDeniedError,
)

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


# Whatever actually went wrong, in the words it was raised with — the screen
# shows the message the server sends, so a fixed "something went wrong" would
# hide the one useful line. A database error is read off its driver exception
# (`orig`), which is the single sentence — "null value in column ... violates
# not-null constraint" — rather than the whole statement and its parameters.
def said_by(error: Exception) -> str:
    said = str(getattr(error, "orig", error) or "").strip()
    if not said:
        return ""

    first = said.splitlines()[0].strip()

    return first[:300]


# Every error answers in one shape. `message` is the contract — the same key
# 7Seers-SkillsBridge answers with, so a client written against either service
# reads the other without changing. `code`, `field` and `errors` ride along for
# the form screens, which highlight the box that was refused; a reader that only
# knows `message` is unaffected by them.
def problem(
    code: str,
    message: str,
    http_status: int,
    field: str = "",
    errors: list[dict] | None = None,
) -> JSONResponse:
    body: dict = {"message": message, "code": code}
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

    # The services raise these to say what went wrong; mapping them here once is
    # what lets every route read as the work it does, with no try/except repeated
    # around each call. The message is the one the service raised. Anything NOT
    # on this list is a bug, and still answers 500.
    @app.exception_handler(NotExistError)
    async def on_missing(_: Request, error: NotExistError) -> JSONResponse:
        return problem("not_found", str(error) or "Not found", status.HTTP_404_NOT_FOUND)

    @app.exception_handler(AlreadyExistError)
    async def on_duplicate(_: Request, error: AlreadyExistError) -> JSONResponse:
        return problem("conflict", str(error) or FALLBACK, status.HTTP_409_CONFLICT)

    @app.exception_handler(AuthenticationError)
    async def on_unauthenticated(_: Request, error: AuthenticationError) -> JSONResponse:
        return problem("unauthenticated", str(error) or FALLBACK, status.HTTP_401_UNAUTHORIZED)

    @app.exception_handler(PermissionDeniedError)
    async def on_denied(_: Request, error: PermissionDeniedError) -> JSONResponse:
        return problem("forbidden", str(error) or FALLBACK, status.HTTP_403_FORBIDDEN)

    @app.exception_handler(InvalidInputError)
    async def on_bad_input(_: Request, error: InvalidInputError) -> JSONResponse:
        return problem("bad_request", str(error) or FALLBACK, status.HTTP_400_BAD_REQUEST)

    @app.exception_handler(SQLAlchemyError)
    async def on_db_error(_: Request, error: SQLAlchemyError) -> JSONResponse:
        LOGGER.exception("database call failed", exc_info=error)

        return problem(
            "database_unavailable",
            said_by(error) or DB_DOWN,
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    @app.exception_handler(Exception)
    async def on_unexpected(_: Request, error: Exception) -> JSONResponse:
        LOGGER.exception("unhandled request error", exc_info=error)

        return problem(
            "server_error",
            said_by(error) or SERVER_ERROR,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
