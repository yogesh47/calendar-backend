from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.auth.deps import require_role
from app.auth.tokens import read_token
from app.auth.users import STUDENT, TPO, HardcodedUser, find_by_id
from app.db.session import get_db
from app.models.calendar_model import (
    ApplicationOut,
    AudienceCountIn,
    AudienceCountOut,
    CancelIn,
    DeleteManyIn,
    DeleteOut,
    DeviceIn,
    DeviceOut,
    EventIn,
    EventOut,
    NotificationOut,
    UnreadOut,
)
from app.services import calendar_service, live_stream, push

router = APIRouter(prefix="/calendar", tags=["calendar"])

# Everything below is event content, so only a TPO or a student may reach it.
calendar_user = require_role(TPO, STUDENT)


# Returns every event, reminder and job deadline the signed-in user is allowed to see.
# `from_date` / `to_date` narrow it to one month, which is what the mobile screen asks for.
@router.get("/events", response_model=list[EventOut])
def list_events(
    user: Annotated[HardcodedUser, Depends(calendar_user)],
    db: Annotated[Session, Depends(get_db)],
    from_date: date | None = None,
    to_date: date | None = None,
) -> list[EventOut]:
    return calendar_service.list_items(db, user, start=from_date, end=to_date)


# The mobile dashboard's "Coming Up" card: the next few items that still apply.
@router.get("/coming-up", response_model=list[EventOut])
def coming_up(
    user: Annotated[HardcodedUser, Depends(calendar_user)],
    db: Annotated[Session, Depends(get_db)],
    limit: int = 3,
) -> list[EventOut]:
    return calendar_service.coming_up(db, user, max(1, min(limit, 20)))


# Tells the TPO how many students match an audience before the event is created.
@router.post("/audience/count", response_model=AudienceCountOut)
def count_audience(payload: AudienceCountIn, _: Annotated[HardcodedUser, Depends(require_role(TPO))]) -> AudienceCountOut:
    return AudienceCountOut(count=calendar_service.audience_count(payload.audience))


# Creates an event (TPO only) or a private reminder, then wakes up every open calendar.
@router.post("/events", response_model=EventOut, status_code=status.HTTP_201_CREATED)
def create_event(
    payload: EventIn,
    user: Annotated[HardcodedUser, Depends(calendar_user)],
    db: Annotated[Session, Depends(get_db)],
) -> EventOut:
    if payload.event_type != "my_reminder" and user.role != TPO:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only a TPO can create events")

    try:
        created = calendar_service.create_event(db, user, payload)
    except ValueError as bad:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(bad))
    live_stream.publish(user.org_id, created.event_id)

    return created


# Edits an existing event or the owner's own reminder.
@router.put("/events/{event_id}", response_model=EventOut)
def update_event(
    event_id: str,
    payload: EventIn,
    user: Annotated[HardcodedUser, Depends(calendar_user)],
    db: Annotated[Session, Depends(get_db)],
) -> EventOut:
    if payload.event_type != "my_reminder" and user.role != TPO:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only a TPO can edit events")

    try:
        updated = calendar_service.update_event(db, user, event_id, payload)
    except LookupError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Event not found")
    except PermissionError as denied:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(denied))
    except ValueError as bad:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(bad))

    live_stream.publish(user.org_id, updated.event_id)

    return updated


# Cancels an event with a reason; the item stays on the calendar as cancelled.
@router.post("/events/{event_id}/cancel", response_model=EventOut)
def cancel_event(
    event_id: str,
    payload: CancelIn,
    user: Annotated[HardcodedUser, Depends(require_role(TPO))],
    db: Annotated[Session, Depends(get_db)],
) -> EventOut:
    try:
        cancelled = calendar_service.cancel_event(db, user, event_id, payload.reason, payload.note)
    except LookupError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Event not found")
    except PermissionError as denied:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(denied))
    except ValueError as bad:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(bad))

    live_stream.publish(user.org_id, cancelled.event_id)

    return cancelled


# Permanently deletes one reminder, or a cancelled event the TPO created.
@router.delete("/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_one(
    event_id: str,
    user: Annotated[HardcodedUser, Depends(calendar_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    try:
        calendar_service.delete_item(db, user, event_id)
    except LookupError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    except PermissionError as denied:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(denied))
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "That id is not valid")

    live_stream.publish(user.org_id, event_id)


# Permanently deletes several items in one call and reports what was skipped.
@router.post("/events/bulk-delete", response_model=DeleteOut)
def delete_many(
    payload: DeleteManyIn,
    user: Annotated[HardcodedUser, Depends(require_role(TPO))],
    db: Annotated[Session, Depends(get_db)],
) -> DeleteOut:
    result = calendar_service.delete_many(db, user, payload.event_ids)
    live_stream.publish(user.org_id, "bulk-delete")

    return DeleteOut(deleted=result["deleted"], skipped=result["skipped"], count=len(result["deleted"]))


# Wipes the org's events and the caller's own reminders; needs ?confirm=yes.
@router.delete("/events", response_model=DeleteOut)
def delete_all(
    user: Annotated[HardcodedUser, Depends(require_role(TPO))],
    db: Annotated[Session, Depends(get_db)],
    confirm: str = "",
) -> DeleteOut:
    if confirm != "yes":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Add ?confirm=yes to wipe every event")

    count = calendar_service.delete_everything(db, user)
    live_stream.publish(user.org_id, "delete-all")

    return DeleteOut(count=count)


# Returns the signed-in student's notifications, newest first.
@router.get("/notifications", response_model=list[NotificationOut])
def list_notifications(
    user: Annotated[HardcodedUser, Depends(calendar_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[NotificationOut]:
    return calendar_service.notifications_for(db, user)


# The red dot on the mobile calendar icon — how many notifications are still unread.
@router.get("/notifications/unread-count", response_model=UnreadOut)
def unread_count(
    user: Annotated[HardcodedUser, Depends(calendar_user)],
    db: Annotated[Session, Depends(get_db)],
) -> UnreadOut:
    return UnreadOut(unread=calendar_service.unread_count(db, user))


# Marks one notification as read.
@router.post("/notifications/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
def read_notification(
    notification_id: str,
    user: Annotated[HardcodedUser, Depends(calendar_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    try:
        calendar_service.mark_seen(db, user, notification_id)
    except ValueError as bad:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(bad))


# Marks every notification of the user as read.
@router.post("/notifications/read-all", status_code=status.HTTP_204_NO_CONTENT)
def read_all_notifications(
    user: Annotated[HardcodedUser, Depends(calendar_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    calendar_service.mark_all_seen(db, user)


# Demo "apply" — the Jobs service owns this in the real app. Applying takes the deadline
# off the student's calendar, along with their pending nudges for it.
@router.post("/jobs/{job_id}/apply", response_model=ApplicationOut, status_code=status.HTTP_201_CREATED)
def apply_to_job(
    job_id: str,
    user: Annotated[HardcodedUser, Depends(require_role(STUDENT))],
    db: Annotated[Session, Depends(get_db)],
) -> ApplicationOut:
    try:
        entry = calendar_service.apply_to_job(db, user, job_id)
    except LookupError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")

    live_stream.publish(user.org_id, "application")

    return entry


# Withdrawing the application brings the deadline back.
@router.delete("/jobs/{job_id}/apply", status_code=status.HTTP_204_NO_CONTENT)
def withdraw_application(
    job_id: str,
    user: Annotated[HardcodedUser, Depends(require_role(STUDENT))],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    calendar_service.withdraw_application(db, user, job_id)
    live_stream.publish(user.org_id, "application")


# The mobile app registers its push token here so nudges can reach the phone.
@router.post("/push/devices", response_model=DeviceOut, status_code=status.HTTP_201_CREATED)
def register_device(
    payload: DeviceIn,
    user: Annotated[HardcodedUser, Depends(calendar_user)],
    db: Annotated[Session, Depends(get_db)],
) -> DeviceOut:
    return push.register(db, user, payload)


# Logging out of the app drops its token again.
@router.delete("/push/devices/{token}", status_code=status.HTTP_204_NO_CONTENT)
def forget_device(
    token: str,
    user: Annotated[HardcodedUser, Depends(calendar_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    push.forget(db, user, token)


# Keeps an SSE connection open so a calendar refreshes the moment anything changes.
@router.get("/stream")
async def stream(request: Request) -> StreamingResponse:
    token = request.query_params.get("token", "")
    claims = read_token(token)
    user = find_by_id(str(claims.get("sub", ""))) if claims else None
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Your session has expired")

    if user.role not in (TPO, STUDENT):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You do not have access to this")

    queue = live_stream.subscribe(user.org_id)

    return StreamingResponse(
        live_stream.stream(user.org_id, queue),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
