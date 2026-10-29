from datetime import date, datetime, timedelta, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import FileResponse, Response, StreamingResponse
from sqlalchemy.orm import Session

from app.auth.deps import require_role
from app.auth.tokens import issue_feed_token, read_feed_token, read_token
from app.auth.users import STUDENT, TPO, SignedInUser, find_by_id
from app.conf import PUBLIC_API_URL
from app.db.session import SessionLocal, get_db
from app.exceptions import AuthenticationError, InvalidInputError, PermissionDeniedError
from app.models.calendar_model import (
    ApplicationOut,
    AudienceCountIn,
    AudienceCountOut,
    AudienceSetIn,
    CancelIn,
    DeleteManyIn,
    DeleteOut,
    DeviceIn,
    DeviceOut,
    EventIn,
    EventOut,
    FeedLinkOut,
    FeedSettingsIn,
    FeedSettingsOut,
    ImageIn,
    ImageOut,
    NotificationOut,
    UnreadOut,
)
from app.services import (
    calendar_service,
    ics,
    images,
    live_stream,
    push,
    settings_service,
)
from app.services.clock import local_date

router = APIRouter(prefix="/calendar", tags=["calendar"])

# Everything below is event content, so only a TPO or a student may reach it.
calendar_user = require_role(TPO, STUDENT)


# Returns every event, reminder and job deadline the signed-in user is allowed to see.
# `from_date` / `to_date` narrow it to one month, which is what the mobile screen asks for.
@router.get("/events")
def list_events(
    user: Annotated[SignedInUser, Depends(calendar_user)],
    db: Annotated[Session, Depends(get_db)],
    from_date: date | None = None,
    to_date: date | None = None,
) -> list[EventOut]:
    return calendar_service.list_items(db, user, start=from_date, end=to_date)


# The mobile dashboard's "Coming Up" card: the next few items that still apply.
@router.get("/coming-up")
def coming_up(
    user: Annotated[SignedInUser, Depends(calendar_user)],
    db: Annotated[Session, Depends(get_db)],
    limit: int = 3,
) -> list[EventOut]:
    return calendar_service.coming_up(db, user, max(1, min(limit, 20)))


# Tells the TPO how many students match an audience before the event is created.
@router.post("/audience/count")
def count_audience(payload: AudienceCountIn, _: Annotated[SignedInUser, Depends(require_role(TPO))]) -> AudienceCountOut:
    return AudienceCountOut(count=calendar_service.audience_count(payload.audience))


# Creates an event (TPO only) or a private reminder, then wakes up every open calendar.
@router.post("/events", status_code=status.HTTP_201_CREATED)
def create_event(
    payload: EventIn,
    user: Annotated[SignedInUser, Depends(calendar_user)],
    db: Annotated[Session, Depends(get_db)],
) -> EventOut:
    if payload.event_type != "my_reminder" and user.role != TPO:
        raise PermissionDeniedError("Only a TPO can create events")

    created = calendar_service.create_event(db, user, payload)
    live_stream.publish(user.org_id, created.event_id)

    return created


# Edits an existing event or the owner's own reminder.
@router.put("/events/{event_id}")
def update_event(
    event_id: str,
    payload: EventIn,
    user: Annotated[SignedInUser, Depends(calendar_user)],
    db: Annotated[Session, Depends(get_db)],
) -> EventOut:
    if payload.event_type != "my_reminder" and user.role != TPO:
        raise PermissionDeniedError("Only a TPO can edit events")

    updated = calendar_service.update_event(db, user, event_id, payload)
    live_stream.publish(user.org_id, updated.event_id)

    return updated


# The step after publishing: who the event reaches. Saving notifies them.
@router.put("/events/{event_id}/audience")
def set_audience(
    event_id: str,
    payload: AudienceSetIn,
    user: Annotated[SignedInUser, Depends(require_role(TPO))],
    db: Annotated[Session, Depends(get_db)],
) -> EventOut:
    updated = calendar_service.set_audience(db, user, event_id, payload.audience)
    live_stream.publish(user.org_id, updated.event_id)

    return updated


# Stores an image for an event and answers the path to put on it.
@router.post("/images", status_code=status.HTTP_201_CREATED)
def upload_image(payload: ImageIn, _: Annotated[SignedInUser, Depends(calendar_user)]) -> ImageOut:
    return ImageOut(image_url=images.save(payload.data_url))


# Serves an event image. Open on purpose: an <img> tag cannot send a token, and
# the names are random 128-bit ids, not guessable ones.
@router.get("/images/{name}")
def read_image(name: str) -> FileResponse:
    path, media_type = images.path_of(name)

    return FileResponse(path, media_type=media_type, headers={"Cache-Control": "public, max-age=31536000, immutable"})


# The signed-in user's personal subscription URL for Google Calendar / Outlook.
@router.get("/feed/link")
def feed_link(request: Request, user: Annotated[SignedInUser, Depends(calendar_user)]) -> FeedLinkOut:
    base = PUBLIC_API_URL or str(request.base_url).rstrip("/")
    return FeedLinkOut(url=f"{base}/calendar/feed.ics?token={issue_feed_token(user)}")


# What the signed-in user's calendar-sync feed carries.
@router.get("/feed/settings")
def read_feed_settings(
    user: Annotated[SignedInUser, Depends(calendar_user)], db: Annotated[Session, Depends(get_db)]
) -> FeedSettingsOut:
    return settings_service.feed_settings(db, user)


# Their own choices; an app already subscribed picks them up on its next refresh.
@router.put("/feed/settings")
def save_feed_settings(
    payload: FeedSettingsIn,
    user: Annotated[SignedInUser, Depends(calendar_user)],
    db: Annotated[Session, Depends(get_db)],
) -> FeedSettingsOut:
    return settings_service.save_feed_settings(db, user, payload)


# The .ics feed itself. Calendar apps poll this; the token in the URL says whose it is.
@router.get("/feed.ics")
def feed(token: str, db: Annotated[Session, Depends(get_db)]) -> Response:
    claims = read_feed_token(token)
    user = find_by_id(db, str(claims.get("sub", ""))) if claims else None
    if not user or user.role not in (TPO, STUDENT):
        raise AuthenticationError("This calendar link is no longer valid")

    chosen = settings_service.feed_settings(db, user)
    today = local_date(datetime.now(timezone.utc), calendar_service.viewer_zone(db, user))  # noqa: UP017
    items = calendar_service.list_items(
        db, user, today - timedelta(days=chosen.past_days), today + timedelta(days=chosen.future_days)
    )
    kinds = {kind for kind in ("events", "deadlines", "reminders") if getattr(chosen, kind)}
    body = ics.build(items, "Campus Calendar", show_cancelled=chosen.cancelled, kinds=kinds)

    return Response(
        content=body,
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": 'inline; filename="campus-calendar.ics"'},
    )


# Cancels an event with a reason; the item stays on the calendar as cancelled.
@router.post("/events/{event_id}/cancel")
def cancel_event(
    event_id: str,
    payload: CancelIn,
    user: Annotated[SignedInUser, Depends(require_role(TPO))],
    db: Annotated[Session, Depends(get_db)],
) -> EventOut:
    cancelled = calendar_service.cancel_event(db, user, event_id, payload.reason, payload.note, payload.scope)
    live_stream.publish(user.org_id, cancelled.event_id)

    return cancelled


# Permanently deletes one reminder, or a cancelled event the TPO created.
# `scope=series` on a repeating reminder takes this date and every later one.
@router.delete("/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_one(
    event_id: str,
    user: Annotated[SignedInUser, Depends(calendar_user)],
    db: Annotated[Session, Depends(get_db)],
    scope: Literal["one", "series"] = "one",
) -> None:
    calendar_service.delete_item(db, user, event_id, scope)
    live_stream.publish(user.org_id, event_id)


# Permanently deletes several items in one call and reports what was skipped.
@router.post("/events/bulk-delete")
def delete_many(
    payload: DeleteManyIn,
    user: Annotated[SignedInUser, Depends(require_role(TPO))],
    db: Annotated[Session, Depends(get_db)],
) -> DeleteOut:
    result = calendar_service.delete_many(db, user, payload.event_ids)
    live_stream.publish(user.org_id, "bulk-delete")

    return DeleteOut(deleted=result["deleted"], skipped=result["skipped"], count=len(result["deleted"]))


# Wipes the org's events and the caller's own reminders; needs ?confirm=yes.
@router.delete("/events")
def delete_all(
    user: Annotated[SignedInUser, Depends(require_role(TPO))],
    db: Annotated[Session, Depends(get_db)],
    confirm: str = "",
) -> DeleteOut:
    if confirm != "yes":
        raise InvalidInputError("Add ?confirm=yes to wipe every event")

    count = calendar_service.delete_everything(db, user)
    live_stream.publish(user.org_id, "delete-all")

    return DeleteOut(count=count)


# Returns the signed-in student's notifications, newest first.
@router.get("/notifications")
def list_notifications(
    user: Annotated[SignedInUser, Depends(calendar_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[NotificationOut]:
    return calendar_service.notifications_for(db, user)


# The red dot on the mobile calendar icon — how many notifications are still unread.
@router.get("/notifications/unread-count")
def unread_count(
    user: Annotated[SignedInUser, Depends(calendar_user)],
    db: Annotated[Session, Depends(get_db)],
) -> UnreadOut:
    return UnreadOut(unread=calendar_service.unread_count(db, user))


# Marks one notification as read.
@router.post("/notifications/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
def read_notification(
    notification_id: str,
    user: Annotated[SignedInUser, Depends(calendar_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    calendar_service.mark_seen(db, user, notification_id)


# Marks every notification of the user as read.
@router.post("/notifications/read-all", status_code=status.HTTP_204_NO_CONTENT)
def read_all_notifications(
    user: Annotated[SignedInUser, Depends(calendar_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    calendar_service.mark_all_seen(db, user)


# Demo "apply" — the Jobs service owns this in the real app. Applying takes the deadline
# off the student's calendar, along with their pending nudges for it.
@router.post("/jobs/{job_id}/apply", status_code=status.HTTP_201_CREATED)
def apply_to_job(
    job_id: str,
    user: Annotated[SignedInUser, Depends(require_role(STUDENT))],
    db: Annotated[Session, Depends(get_db)],
) -> ApplicationOut:
    entry = calendar_service.apply_to_job(db, user, job_id)
    live_stream.publish(user.org_id, "application")

    return entry


# Withdrawing the application brings the deadline back.
@router.delete("/jobs/{job_id}/apply", status_code=status.HTTP_204_NO_CONTENT)
def withdraw_application(
    job_id: str,
    user: Annotated[SignedInUser, Depends(require_role(STUDENT))],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    calendar_service.withdraw_application(db, user, job_id)
    live_stream.publish(user.org_id, "application")


# The mobile app registers its push token here so nudges can reach the phone.
@router.post("/push/devices", status_code=status.HTTP_201_CREATED)
def register_device(
    payload: DeviceIn,
    user: Annotated[SignedInUser, Depends(calendar_user)],
    db: Annotated[Session, Depends(get_db)],
) -> DeviceOut:
    return push.register(db, user, payload)


# Logging out of the app drops its token again.
@router.delete("/push/devices/{token}", status_code=status.HTTP_204_NO_CONTENT)
def forget_device(
    token: str,
    user: Annotated[SignedInUser, Depends(calendar_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    push.forget(db, user, token)


# Keeps an SSE connection open so a calendar refreshes the moment anything changes.
@router.get("/stream")
async def stream(request: Request) -> StreamingResponse:
    # The browser's EventSource cannot send an Authorization header, so the token
    # rides in the query string — the same token, read the same way.
    token = request.query_params.get("token", "")
    claims = read_token(token)
    # Its own short session, closed before streaming starts. Taking it from
    # get_db held a pool connection for as long as the tab stayed open, and a
    # handful of open tabs used the whole pool up — every other request then
    # waited forever for a connection.
    with SessionLocal() as db:
        user = find_by_id(db, str(claims.get("sub", ""))) if claims else None
    if not user:
        raise AuthenticationError("Your session has expired")

    if user.role not in (TPO, STUDENT):
        raise PermissionDeniedError("You do not have access to this")

    queue = live_stream.subscribe(user.org_id)

    return StreamingResponse(
        live_stream.stream(user.org_id, queue),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
