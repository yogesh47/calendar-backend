import uuid
from datetime import datetime, time, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.users import HardcodedUser, TPO, find_by_id
from app.db.models import CalendarEvent, CalendarEventAudience, CalendarEventRecipient, CalendarReminder
from app.models.calendar_model import AudienceIn, EventIn, EventOut, LinkedJobIn, NotificationOut
from app.services.clock import local_date, local_time, to_utc
from app.services.companies import company_id_of, company_name_of
from app.services.students import count_audience, matching_student_ids

CANCEL_REASON_LABEL = {
    "postponed": "Postponed",
    "company_withdrew": "Company withdrew",
    "created_by_mistake": "Created by mistake",
    "other": "Other",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


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


def event_out(db: Session, event: CalendarEvent, viewer: HardcodedUser) -> EventOut:
    audience = _audience_of(db, event.event_id)
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
        is_owner=str(reminder.owner_id) == viewer.user_id,
    )


def list_items(db: Session, viewer: HardcodedUser) -> list[EventOut]:
    events = list(db.scalars(select(CalendarEvent).where(CalendarEvent.org_id == viewer.org_id)))

    if viewer.role != TPO:
        mine = {
            str(row.event_id)
            for row in db.scalars(
                select(CalendarEventRecipient).where(
                    CalendarEventRecipient.student_id == viewer.user_id,
                    CalendarEventRecipient.state == "active",
                )
            )
        }
        events = [
            event
            for event in events
            if str(event.event_id) in mine and event.cancel_reason != "created_by_mistake"
        ]

    reminders = list(
        db.scalars(select(CalendarReminder).where(CalendarReminder.owner_id == viewer.user_id))
    )

    return [event_out(db, event, viewer) for event in events] + [
        reminder_out(reminder, viewer) for reminder in reminders
    ]


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
        )
        db.add(reminder)
        db.commit()
        db.refresh(reminder)

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

    return event_out(db, event, user)


def update_event(db: Session, user: HardcodedUser, event_id: str, payload: EventIn) -> EventOut:
    reminder = db.get(CalendarReminder, uuid.UUID(event_id))
    if reminder:
        reminder.title = payload.title
        reminder.reminder_date = payload.event_date
        reminder.reminder_time = payload.start_time
        reminder.note = payload.note
        db.commit()
        db.refresh(reminder)

        return reminder_out(reminder, user)

    event = db.get(CalendarEvent, uuid.UUID(event_id))
    if not event:
        raise LookupError("Event not found")

    apply_payload(event, payload)

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

    return event_out(db, event, user)


def cancel_event(db: Session, user: HardcodedUser, event_id: str, reason: str, note: str | None) -> EventOut:
    event = db.get(CalendarEvent, uuid.UUID(event_id))
    if not event:
        raise LookupError("Event not found")

    event.status = "cancelled"
    event.cancel_reason = reason
    event.cancel_note = note
    event.cancelled_by = uuid.UUID(user.user_id)
    event.cancelled_at = _now()
    db.commit()
    db.refresh(event)

    return event_out(db, event, user)


def delete_reminder(db: Session, user: HardcodedUser, reminder_id: str) -> None:
    reminder = db.get(CalendarReminder, uuid.UUID(reminder_id))
    if not reminder or str(reminder.owner_id) != user.user_id:
        raise LookupError("Reminder not found")

    db.delete(reminder)
    db.commit()


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
            message = f"Please ignore the earlier notification about {event.title}."
        elif event.status == "cancelled":
            message = (
                f"{event.title} on {event.event_date:%d %b} has been cancelled. "
                f"Reason: {CANCEL_REASON_LABEL.get(event.cancel_reason or '', 'Other')}."
            )
        elif row.state == "removed":
            message = f"{event.title} on {event.event_date:%d %b} no longer applies to you."
        elif event.updated_at > event.created_at:
            message = f"{event.title} has been updated."
        else:
            message = f"New event: {event.title} on {event.event_date:%d %b}{start}. Check your Campus Calendar."

        changed_at = event.cancelled_at or event.updated_at
        out.append(
            NotificationOut(
                notification_id=str(row.recipient_id),
                event_id=str(event.event_id),
                message=message,
                created_at=changed_at,
                is_read=bool(row.seen_at and row.seen_at >= changed_at),
            )
        )

    return sorted(out, key=lambda entry: entry.created_at, reverse=True)


def mark_seen(db: Session, viewer: HardcodedUser, notification_id: str) -> None:
    row = db.get(CalendarEventRecipient, uuid.UUID(notification_id))
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
    db.commit()
