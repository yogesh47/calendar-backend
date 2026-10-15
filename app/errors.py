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

    if kind.startswith("string_too_long") or kind.startswith("too_long"):
        return f"{field_label(tuple(error.get('loc', ())))} is too long"

    if kind in ("literal_error", "enum"):
        return f"{field_label(tuple(error.get('loc', ())))} has an unexpected value"

    if kind.endswith("_parsing") or kind.endswith("_type"):
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
