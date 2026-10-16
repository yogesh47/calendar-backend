import uuid
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.users import TPO, HardcodedUser, find_by_id
from app.db.models import (
    CalendarEvent,
    CalendarEventAudience,
    CalendarEventRecipient,
    CalendarNudge,
    CalendarReminder,
)
from app.models.calendar_model import (
    ApplicationOut,
    AudienceIn,
    EventIn,
    EventOut,
    LinkedJobIn,
    NotificationOut,
)
from app.services import deadlines, nudges
from app.services.clock import local_date, local_time, to_utc
from app.services.companies import company_id_of, company_name_of
from app.services.ids import as_uuid
from app.services.jobs import apply_to, job_by_id
from app.services.jobs import withdraw as withdraw_from
from app.services.students import count_audience, matching_student_ids

CANCEL_REASON_LABEL = {
    "postponed": "Postponed",
    "company_withdrew": "Company withdrew",
    "created_by_mistake": "Created by mistake",
    "other": "Other",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)  # noqa: UP017 - datetime.UTC needs Python 3.11


def _text(value: time | None) -> str | None:
    return value.strftime("%H:%M") if value else None


def _name_of(user_id) -> str:
    user = find_by_id(str(user_id))

    return user.name if user else "TPO"





def audience_count(audience: AudienceIn) -> int:
    return count_audience(audience.courses, audience.batches, audience.departments)


def _audience_of(db: Session, event_id) -> CalendarEventAudience | None:
    return db.scalar(select(CalendarEventAudience).where(CalendarEventAudience.event_id == event_id))


def _recipient_count(db: Session, event_id) -> int:
    return (
        db.query(CalendarEventRecipient)
        .filter(CalendarEventRecipient.event_id == event_id, CalendarEventRecipient.state == "active")
        .count()
    )


def _recipient_of(db: Session, event_id, student_id: str) -> CalendarEventRecipient | None:
    return db.scalar(
        select(CalendarEventRecipient).where(
            CalendarEventRecipient.event_id == event_id,
            CalendarEventRecipient.student_id == student_id,
        )
    )


def event_out(db: Session, event: CalendarEvent, viewer: HardcodedUser) -> EventOut:
    audience = _audience_of(db, event.event_id)
    mine = _recipient_of(db, event.event_id, viewer.user_id) if viewer.role != TPO else None
    linked = None
    if event.linked_job_kind:
        linked = LinkedJobIn(
            kind=event.linked_job_kind,
            campus_job=event.linked_job_title if event.linked_job_kind == "campus" else None,
            url=event.linked_job_url,
            title=event.linked_job_title,
        )

    stored = audience_count(
        AudienceIn(
            opportunity_type=audience.opportunity_type,
            courses=list(audience.courses),
            batches=list(audience.batches),
            departments=list(audience.departments),
        )
    ) if audience else 0

    return EventOut(
        event_id=str(event.event_id),
        event_type=event.event_type,
        title=event.title,
        company=company_name_of(event.company_id),
        event_date=event.event_date,
        end_date=local_date(event.end_at) or event.event_date,
        start_time=local_time(event.start_at),
        end_time=local_time(event.end_at),
        mode=event.mode,
        venue=event.venue,
        online_platform=event.online_platform,
        description=event.description,
        note=None,
        status=event.status,
        cancel_reason=event.cancel_reason,
        cancel_note=event.cancel_note,
        cancelled_at=event.cancelled_at,
        created_by=str(event.created_by),
        created_by_name=_name_of(event.created_by),
        created_at=event.created_at,
        updated_at=event.updated_at,
        change_summary=event.change_summary,
        change_reason=event.change_reason,
        notified_count=stored or _recipient_count(db, event.event_id),
        audience=AudienceIn(
            opportunity_type=audience.opportunity_type,
            courses=list(audience.courses),
            batches=list(audience.batches),
            departments=list(audience.departments),
        )
        if audience
        else None,
        linked_job=linked,
        is_owner=str(event.created_by) == viewer.user_id,
        applies_to_me=mine.state == "active" if mine else True,
        removed_reason=mine.removed_reason if mine and mine.state == "removed" else None,
    )


def reminder_out(reminder: CalendarReminder, viewer: HardcodedUser) -> EventOut:
    return EventOut(
        event_id=str(reminder.reminder_id),
        event_type="my_reminder",
        title=reminder.title,
        company=None,
        event_date=reminder.reminder_date,
        end_date=reminder.reminder_date,
        start_time=_text(reminder.reminder_time),
        end_time=None,
        mode=None,
        venue=None,
        online_platform=None,
        description=None,
        note=reminder.note,
        status="published",
        cancel_reason=None,
        cancel_note=None,
        cancelled_at=None,
        created_by=str(reminder.owner_id),
        created_by_name=_name_of(reminder.owner_id),
        created_at=reminder.created_at,
        updated_at=reminder.updated_at,
        notified_count=0,
        audience=None,
        linked_job=None,
        remind_before=reminder.remind_before,
        linked_type=reminder.linked_type,
        linked_id=str(reminder.linked_id) if reminder.linked_id else None,
        is_owner=str(reminder.owner_id) == viewer.user_id,
    )


def nudge_out(db: Session, row) -> EventOut:
    moment = row.sent_at or row.scheduled_at

    return EventOut(
        event_id=str(row.nudge_id),
        event_type="nudge",
        title=nudges.message_for(db, row),
        company=None,
        event_date=local_date(moment),
        end_date=local_date(moment),
        start_time=local_time(moment),
        end_time=None,
        mode=None,
        venue=None,
        online_platform=None,
        description=None,
        note=None,
        status="published",
        cancel_reason=None,
        cancel_note=None,
        cancelled_at=None,
        created_by=str(row.student_id),
        created_by_name="7Seers",
        created_at=moment,
        updated_at=moment,
        notified_count=0,
        audience=None,
        linked_job=None,
        remind_before=None,
        linked_type="event" if row.item_type == "event" else "job_deadline",
        linked_id=str(row.item_id),
        is_owner=True,
    )


def within(items: list[EventOut], start: date | None, end: date | None) -> list[EventOut]:
    return [
        item
        for item in items
        if (start is None or (item.end_date or item.event_date) >= start)
        and (end is None or item.event_date <= end)
    ]


def list_items(
    db: Session,
    viewer: HardcodedUser,
    start: date | None = None,
    end: date | None = None,
) -> list[EventOut]:
    events = list(db.scalars(select(CalendarEvent).where(CalendarEvent.org_id == viewer.org_id)))
    sent_nudges = []

    if viewer.role != TPO:
        mine = {
            str(row.event_id)
            for row in db.scalars(
                select(CalendarEventRecipient).where(CalendarEventRecipient.student_id == viewer.user_id)
            )
        }
        events = [
            event
            for event in events
            if str(event.event_id) in mine and event.cancel_reason != "created_by_mistake"
        ]
        sent_nudges = nudges.sent_for(db, viewer.user_id)

    reminders = list(
        db.scalars(select(CalendarReminder).where(CalendarReminder.owner_id == viewer.user_id))
    )

    items = (
        [event_out(db, event, viewer) for event in events]
        + [reminder_out(reminder, viewer) for reminder in reminders]
        + [nudge_out(db, row) for row in sent_nudges]
        + deadlines.deadline_items(viewer)
    )

    return within(items, start, end)


# Applying also clears that student's pending deadline nudges.
def apply_to_job(db: Session, user: HardcodedUser, job_id: str) -> ApplicationOut:
    job = job_by_id(job_id)
    if not job:
        raise LookupError("Job not found")

    entry = apply_to(job_id, user.user_id)
    nudges.drop_for_job(db, job_id, user.user_id)

    return ApplicationOut(
        application_id=entry.application_id, job_id=entry.job_id, application_status=entry.application_status
    )


def withdraw_application(db: Session, user: HardcodedUser, job_id: str) -> None:
    withdraw_from(job_id, user.user_id)
    nudges.schedule_deadlines(db, user.org_id)


# The mobile "Coming Up" card: the next few items the viewer still cares about.
def coming_up(db: Session, viewer: HardcodedUser, limit: int = 3) -> list[EventOut]:
    today = local_date(_now())
    upcoming = [
        item
        for item in list_items(db, viewer, start=today)
        if item.status != "cancelled" and item.applies_to_me and item.event_type != "nudge"
    ]
    upcoming.sort(key=lambda item: (item.event_date, item.start_time or "00:00"))

    return upcoming[:limit]


def unread_count(db: Session, viewer: HardcodedUser) -> int:
    return len([entry for entry in notifications_for(db, viewer) if not entry.is_read])


def sync_recipients(db: Session, event: CalendarEvent, audience: AudienceIn) -> None:
    wanted = set(matching_student_ids(audience.courses, audience.batches, audience.departments))
    existing = {
        str(row.student_id): row
        for row in db.scalars(
            select(CalendarEventRecipient).where(CalendarEventRecipient.event_id == event.event_id)
        )
    }

    for student_id in wanted - set(existing):
        db.add(
            CalendarEventRecipient(
                org_id=event.org_id,
                event_id=event.event_id,
                student_id=uuid.UUID(student_id),
                state="active",
            )
        )

    for student_id, row in existing.items():
        row.state = "active" if student_id in wanted else "removed"
        if student_id not in wanted:
            row.seen_at = None


def apply_change_notes(event: CalendarEvent, payload: EventIn) -> None:
    event.change_summary = payload.change_summary
    event.change_reason = payload.change_reason
    event.notify_on_change = payload.notify_on_change


def apply_payload(event: CalendarEvent, payload: EventIn) -> None:
    event.event_type = payload.event_type
    event.title = payload.title
    event.company_id = company_id_of(payload.company)
    event.event_date = payload.event_date
    event.start_at = to_utc(payload.event_date, payload.start_time)
    event.end_at = to_utc(payload.end_date or payload.event_date, payload.end_time)
    event.mode = payload.mode
    event.venue = payload.venue
    event.online_platform = payload.online_platform
    event.description = payload.description
    event.linked_job_kind = payload.linked_job.kind if payload.linked_job else None
    event.linked_job_url = payload.linked_job.url if payload.linked_job else None
    event.linked_job_title = (
        (payload.linked_job.campus_job if payload.linked_job.kind == "campus" else payload.linked_job.title)
        if payload.linked_job
        else None
    )


def create_event(db: Session, user: HardcodedUser, payload: EventIn) -> EventOut:
    if payload.event_type == "my_reminder":
        reminder = CalendarReminder(
            org_id=uuid.UUID(user.org_id),
            owner_id=uuid.UUID(user.user_id),
            owner_role=user.role,
            title=payload.title,
            reminder_date=payload.event_date,
            reminder_time=payload.start_time,
            note=payload.note,
            remind_before=payload.remind_before or "none",
            linked_type=payload.linked_type,
            linked_id=uuid.UUID(payload.linked_id) if payload.linked_id else None,
        )
        db.add(reminder)
        db.commit()
        db.refresh(reminder)
        nudges.schedule_for_reminder(db, reminder)

        return reminder_out(reminder, user)

    event = CalendarEvent(org_id=uuid.UUID(user.org_id), created_by=uuid.UUID(user.user_id))
    apply_payload(event, payload)
    db.add(event)
    db.flush()

    if payload.audience:
        db.add(
            CalendarEventAudience(
                event_id=event.event_id,
                opportunity_type=payload.audience.opportunity_type,
                courses=payload.audience.courses,
                batches=payload.audience.batches,
                departments=payload.audience.departments,
            )
        )
        sync_recipients(db, event, payload.audience)

    db.commit()
    db.refresh(event)
    nudges.schedule_for_event(db, event)

    return event_out(db, event, user)


def update_event(db: Session, user: HardcodedUser, event_id: str, payload: EventIn) -> EventOut:
    key = as_uuid(event_id)
    reminder = db.get(CalendarReminder, key)
    if reminder:
        if str(reminder.owner_id) != user.user_id:
            raise PermissionError("Only the owner can edit this reminder")
        reminder.title = payload.title
        reminder.reminder_date = payload.event_date
        reminder.reminder_time = payload.start_time
        reminder.note = payload.note
        reminder.remind_before = payload.remind_before or "none"
        reminder.linked_type = payload.linked_type
        reminder.linked_id = uuid.UUID(payload.linked_id) if payload.linked_id else None
        db.commit()
        db.refresh(reminder)
        nudges.schedule_for_reminder(db, reminder)

        return reminder_out(reminder, user)

    event = db.get(CalendarEvent, key)
    if not event:
        raise LookupError("Event not found")

    if str(event.created_by) != user.user_id:
        raise PermissionError("Only the TPO who created this event can edit it")

    if event.status == "cancelled":
        raise PermissionError("A cancelled event cannot be edited")

    apply_payload(event, payload)
    apply_change_notes(event, payload)

    if payload.audience:
        audience = _audience_of(db, event.event_id)
        if audience:
            audience.opportunity_type = payload.audience.opportunity_type
            audience.courses = payload.audience.courses
            audience.batches = payload.audience.batches
            audience.departments = payload.audience.departments
        sync_recipients(db, event, payload.audience)

    db.commit()
    db.refresh(event)
    nudges.schedule_for_event(db, event)

    return event_out(db, event, user)


def cancel_event(db: Session, user: HardcodedUser, event_id: str, reason: str, note: str | None) -> EventOut:
    event = db.get(CalendarEvent, as_uuid(event_id))
    if not event:
        raise LookupError("Event not found")

    if str(event.created_by) != user.user_id:
        raise PermissionError("Only the TPO who created this event can cancel it")

    finished = event.end_at or event.start_at
    if finished and finished <= _now():
        raise PermissionError("An event can only be cancelled before it ends")

    event.status = "cancelled"
    event.cancel_reason = reason
    event.cancel_note = note
    event.cancelled_by = uuid.UUID(user.user_id)
    event.cancelled_at = _now()
    db.commit()
    db.refresh(event)
    nudges.schedule_for_event(db, event)

    return event_out(db, event, user)


def delete_reminder(db: Session, user: HardcodedUser, reminder_id: str) -> None:
    reminder = db.get(CalendarReminder, as_uuid(reminder_id))
    if not reminder or str(reminder.owner_id) != user.user_id:
        raise LookupError("Reminder not found")

    db.delete(reminder)
    db.commit()


def delete_item(db: Session, user: HardcodedUser, item_id: str) -> str:
    key = as_uuid(item_id)

    reminder = db.get(CalendarReminder, key)
    if reminder:
        if str(reminder.owner_id) != user.user_id:
            raise PermissionError("Only the owner can delete this reminder")
        db.query(CalendarNudge).filter(CalendarNudge.item_id == key).delete()
        db.delete(reminder)
        db.commit()

        return "reminder"

    event = db.get(CalendarEvent, key)
    if not event:
        raise LookupError("Not found")

    if str(event.created_by) != user.user_id:
        raise PermissionError("Only the TPO who created this event can delete it")

    db.query(CalendarEventRecipient).filter(CalendarEventRecipient.event_id == key).delete()
    db.query(CalendarEventAudience).filter(CalendarEventAudience.event_id == key).delete()
    db.query(CalendarNudge).filter(CalendarNudge.item_id == key).delete()
    db.delete(event)
    db.commit()

    return "event"


def delete_many(db: Session, user: HardcodedUser, item_ids: list[str]) -> dict[str, list[str]]:
    deleted: list[str] = []
    skipped: list[str] = []

    for item_id in item_ids:
        try:
            delete_item(db, user, item_id)
            deleted.append(item_id)
        except (LookupError, PermissionError, ValueError):
            skipped.append(item_id)

    return {"deleted": deleted, "skipped": skipped}


def delete_everything(db: Session, user: HardcodedUser) -> int:
    events = list(db.scalars(select(CalendarEvent).where(CalendarEvent.org_id == uuid.UUID(user.org_id))))
    reminders = list(
        db.scalars(select(CalendarReminder).where(CalendarReminder.owner_id == uuid.UUID(user.user_id)))
    )

    for event in events:
        db.query(CalendarEventRecipient).filter(CalendarEventRecipient.event_id == event.event_id).delete()
        db.query(CalendarEventAudience).filter(CalendarEventAudience.event_id == event.event_id).delete()
        db.query(CalendarNudge).filter(CalendarNudge.item_id == event.event_id).delete()
        db.delete(event)

    for reminder in reminders:
        db.query(CalendarNudge).filter(CalendarNudge.item_id == reminder.reminder_id).delete()
        db.delete(reminder)

    db.commit()

    return len(events) + len(reminders)


def notifications_for(db: Session, viewer: HardcodedUser) -> list[NotificationOut]:
    rows = list(
        db.scalars(
            select(CalendarEventRecipient).where(CalendarEventRecipient.student_id == viewer.user_id)
        )
    )

    out: list[NotificationOut] = []
    for row in rows:
        event = db.get(CalendarEvent, row.event_id)
        if not event:
            continue

        start = f", {local_time(event.start_at)}" if event.start_at else ""
        if event.status == "cancelled" and event.cancel_reason == "created_by_mistake":
            kind = "ignore_earlier"
            message = f"Please ignore the earlier notification about {event.title}."
        elif event.status == "cancelled":
            kind = "event_cancelled"
            message = (
                f"{event.title} on {event.event_date:%d %b} has been cancelled. "
                f"Reason: {CANCEL_REASON_LABEL.get(event.cancel_reason or '', 'Other')}."
            )
        elif row.state == "removed":
            kind = "not_applicable"
            reason = f" {event.change_reason}" if event.change_reason else ""
            message = f"{event.title} on {event.event_date:%d %b} no longer applies to you.{reason}"
        elif row.created_at > event.created_at + timedelta(seconds=5):
            kind = "new_event"
            message = f"New event: {event.title} on {event.event_date:%d %b}{start}."
        elif event.updated_at > event.created_at:
            kind = "event_updated"
            if not event.notify_on_change:
                message = f"{event.title} details have been updated."
            elif event.change_summary:
                message = f"{event.title} has been updated: {event.change_summary}."
            else:
                message = f"{event.title} has been updated."
        else:
            kind = "new_event"
            message = f"New event: {event.title} on {event.event_date:%d %b}{start}. Check your Campus Calendar."

        changed_at = event.cancelled_at or event.updated_at
        out.append(
            NotificationOut(
                notification_id=str(row.recipient_id),
                event_id=str(event.event_id),
                message=message,
                created_at=changed_at,
                is_read=bool(row.seen_at and row.seen_at >= changed_at),
                kind=kind,
            )
        )

    for nudge in nudges.sent_for(db, viewer.user_id):
        out.append(
            NotificationOut(
                notification_id=str(nudge.nudge_id),
                event_id=str(nudge.item_id),
                message=nudges.message_for(db, nudge),
                created_at=nudge.sent_at or nudge.scheduled_at,
                is_read=bool(nudge.seen_at),
                kind=nudge.nudge_type,
            )
        )

    return sorted(out, key=lambda entry: entry.created_at, reverse=True)


def mark_seen(db: Session, viewer: HardcodedUser, notification_id: str) -> None:
    key = as_uuid(notification_id)
    row = db.get(CalendarEventRecipient, key) or db.get(CalendarNudge, key)
    if not row or str(row.student_id) != viewer.user_id:
        return

    row.seen_at = _now()
    db.commit()


def mark_all_seen(db: Session, viewer: HardcodedUser) -> None:
    rows = db.scalars(
        select(CalendarEventRecipient).where(CalendarEventRecipient.student_id == viewer.user_id)
    )
    for row in rows:
        row.seen_at = _now()

    for nudge in nudges.sent_for(db, viewer.user_id):
        nudge.seen_at = _now()

    db.commit()
