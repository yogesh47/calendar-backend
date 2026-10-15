from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.auth.deps import current_user, require_role
from app.auth.tokens import read_token
from app.auth.users import HardcodedUser, TPO, find_by_id
from app.db.session import get_db
from app.models.calendar_model import (
    AudienceCountIn,
    AudienceCountOut,
    CancelIn,
    DeleteManyIn,
    DeleteOut,
    EventIn,
    EventOut,
    NotificationOut,
)
from app.services import calendar_service, live_stream

router = APIRouter(prefix="/calendar", tags=["calendar"])


@router.get("/events", response_model=list[EventOut])
def list_events(
    user: HardcodedUser = Depends(current_user),
    db: Session = Depends(get_db),
) -> list[EventOut]:
    return calendar_service.list_items(db, user)


@router.post("/audience/count", response_model=AudienceCountOut)
def count_audience(payload: AudienceCountIn, _: HardcodedUser = Depends(require_role(TPO))) -> AudienceCountOut:
    return AudienceCountOut(count=calendar_service.audience_count(payload.audience))


@router.post("/events", response_model=EventOut, status_code=status.HTTP_201_CREATED)
def create_event(
    payload: EventIn,
    user: HardcodedUser = Depends(require_role(TPO)),
    db: Session = Depends(get_db),
) -> EventOut:
    created = calendar_service.create_event(db, user, payload)
    live_stream.publish(user.org_id, created.event_id)

    return created


@router.put("/events/{event_id}", response_model=EventOut)
def update_event(
    event_id: str,
    payload: EventIn,
    user: HardcodedUser = Depends(require_role(TPO)),
    db: Session = Depends(get_db),
) -> EventOut:
    try:
        updated = calendar_service.update_event(db, user, event_id, payload)
    except LookupError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Event not found")

    live_stream.publish(user.org_id, updated.event_id)

    return updated


@router.post("/events/{event_id}/cancel", response_model=EventOut)
def cancel_event(
    event_id: str,
    payload: CancelIn,
    user: HardcodedUser = Depends(require_role(TPO)),
    db: Session = Depends(get_db),
) -> EventOut:
    try:
        cancelled = calendar_service.cancel_event(db, user, event_id, payload.reason, payload.note)
    except LookupError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Event not found")

    live_stream.publish(user.org_id, cancelled.event_id)

    return cancelled


@router.delete("/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_one(
    event_id: str,
    user: HardcodedUser = Depends(current_user),
    db: Session = Depends(get_db),
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


@router.post("/events/bulk-delete", response_model=DeleteOut)
def delete_many(
    payload: DeleteManyIn,
    user: HardcodedUser = Depends(require_role(TPO)),
    db: Session = Depends(get_db),
) -> DeleteOut:
    result = calendar_service.delete_many(db, user, payload.event_ids)
    live_stream.publish(user.org_id, "bulk-delete")

    return DeleteOut(deleted=result["deleted"], skipped=result["skipped"], count=len(result["deleted"]))


@router.delete("/events", response_model=DeleteOut)
def delete_all(
    confirm: str = "",
    user: HardcodedUser = Depends(require_role(TPO)),
    db: Session = Depends(get_db),
) -> DeleteOut:
    if confirm != "yes":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Add ?confirm=yes to wipe every event")

    count = calendar_service.delete_everything(db, user)
    live_stream.publish(user.org_id, "delete-all")

    return DeleteOut(count=count)


@router.get("/notifications", response_model=list[NotificationOut])
def list_notifications(
    user: HardcodedUser = Depends(current_user),
    db: Session = Depends(get_db),
) -> list[NotificationOut]:
    return calendar_service.notifications_for(db, user)


@router.post("/notifications/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
def read_notification(
    notification_id: str,
    user: HardcodedUser = Depends(current_user),
    db: Session = Depends(get_db),
) -> None:
    calendar_service.mark_seen(db, user, notification_id)


@router.post("/notifications/read-all", status_code=status.HTTP_204_NO_CONTENT)
def read_all_notifications(
    user: HardcodedUser = Depends(current_user),
    db: Session = Depends(get_db),
) -> None:
    calendar_service.mark_all_seen(db, user)


@router.get("/stream")
async def stream(request: Request) -> StreamingResponse:
    token = request.query_params.get("token", "")
    claims = read_token(token)
    user = find_by_id(str(claims.get("sub", ""))) if claims else None
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Your session has expired")

    queue = live_stream.subscribe(user.org_id)

    return StreamingResponse(
        live_stream.stream(user.org_id, queue),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
