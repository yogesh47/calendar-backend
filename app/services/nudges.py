import uuid
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.users import HARDCODED_USERS, STUDENT
from app.db.models import (
    CalendarEvent,
    CalendarEventRecipient,
    CalendarNudge,
    CalendarReminder,
)
from app.services import settings_service
from app.services.clock import ORG_TIMEZONE, local_time, to_utc
from app.services.jobs import CAMPUS_JOBS, job_by_id
from app.services.students import STUDENT_PROFILE

EVENT_DAY_BEFORE = "event_day_before"
EVENT_HOUR_BEFORE = "event_hour_before"
ASSESSMENT_DAY = "assessment_day"
DEADLINE_DAYS_BEFORE = "deadline_days_before"
DEADLINE_LAST_DAY = "deadline_last_day"
REMINDER_ALERT = "reminder_alert"

PRIORITY = {
    REMINDER_ALERT: 0,
    DEADLINE_DAYS_BEFORE: 1,
    DEADLINE_LAST_DAY: 1,
    ASSESSMENT_DAY: 2,
    EVENT_DAY_BEFORE: 3,
    EVENT_HOUR_BEFORE: 3,
}

ASSESSMENT_HOUR = time(8, 0)

ALL_DAY_ALERT_HOUR = time(9, 0)

REMIND_BEFORE_OFFSET = {
    "at_time": timedelta(0),
    "15_min": timedelta(minutes=15),
    "1_hour": timedelta(hours=1),
    "1_day": timedelta(days=1),
}

DEADLINE_HOUR = time(9, 0)


def _now() -> datetime:
    return datetime.now(timezone.utc)  # noqa: UP017 - datetime.UTC needs Python 3.11


def _local(moment: datetime) -> datetime:
    return moment.astimezone(ORG_TIMEZONE)


def _add(db: Session, org_id, student_id, nudge_type: str, item_type: str, item_id: str, when: datetime) -> None:
    if when <= _now():
        return

    exists = db.scalar(
        select(CalendarNudge).where(
            CalendarNudge.student_id == uuid.UUID(str(student_id)),
            CalendarNudge.nudge_type == nudge_type,
            CalendarNudge.item_id == uuid.UUID(item_id),
            CalendarNudge.scheduled_at == when,
        )
    )
    if exists:
        return

    db.add(
        CalendarNudge(
            org_id=uuid.UUID(str(org_id)),
            student_id=uuid.UUID(str(student_id)),
            nudge_type=nudge_type,
            item_type=item_type,
            item_id=uuid.UUID(item_id),
            scheduled_at=when,
            status="scheduled",
        )
    )


def _drop_scheduled(db: Session, item_id) -> None:
    db.query(CalendarNudge).filter(
        CalendarNudge.item_id == item_id,
        CalendarNudge.status == "scheduled",
    ).delete()


def schedule_for_event(db: Session, event: CalendarEvent) -> None:
    _drop_scheduled(db, event.event_id)

    if event.status != "published":
        db.commit()
        return

    settings = settings_service.current_row(db)
    recipients = db.scalars(
        select(CalendarEventRecipient).where(
            CalendarEventRecipient.event_id == event.event_id,
            CalendarEventRecipient.state == "active",
        )
    )

    for recipient in recipients:
        if event.start_at:
            _add(
                db,
                event.org_id,
                recipient.student_id,
                EVENT_DAY_BEFORE,
                "event",
                str(event.event_id),
                event.start_at - timedelta(days=settings.event_reminder_days_before),
            )
            _add(
                db,
                event.org_id,
                recipient.student_id,
                EVENT_HOUR_BEFORE,
                "event",
                str(event.event_id),
                event.start_at - timedelta(hours=settings.event_reminder_hours_before),
            )

        if event.event_type == "online_assessment":
            _add(
                db,
                event.org_id,
                recipient.student_id,
                ASSESSMENT_DAY,
                "event",
                str(event.event_id),
                to_utc(event.event_date, ASSESSMENT_HOUR),
            )

    db.commit()


def alert_at(reminder) -> datetime | None:
    if reminder.remind_before in (None, "none"):
        return None

    if reminder.reminder_time:
        moment = to_utc(reminder.reminder_date, reminder.reminder_time)
        return moment - REMIND_BEFORE_OFFSET.get(reminder.remind_before, timedelta(0))

    return to_utc(reminder.reminder_date, ALL_DAY_ALERT_HOUR)


def schedule_for_reminder(db: Session, reminder) -> None:
    _drop_scheduled(db, reminder.reminder_id)
    when = alert_at(reminder)

    if when:
        _add(
            db,
            reminder.org_id,
            reminder.owner_id,
            REMINDER_ALERT,
            "reminder",
            str(reminder.reminder_id),
            when,
        )

    db.commit()


def schedule_deadlines(db: Session, org_id: str) -> None:
    settings = settings_service.current_row(db)
    students = [user for user in HARDCODED_USERS if user.role == STUDENT]

    for job in CAMPUS_JOBS:
        if STUDENT_PROFILE["department"] not in job.departments:
            continue

        for student in students:
            _add(
                db,
                org_id,
                student.user_id,
                DEADLINE_DAYS_BEFORE,
                "job",
                job.job_id,
                to_utc(job.application_end_date - timedelta(days=settings.deadline_reminder_days_before), DEADLINE_HOUR),
            )

            if settings.deadline_reminder_same_day:
                _add(
                    db,
                    org_id,
                    student.user_id,
                    DEADLINE_LAST_DAY,
                    "job",
                    job.job_id,
                    to_utc(job.application_end_date, DEADLINE_HOUR),
                )

    db.commit()


def _still_relevant(db: Session, row: CalendarNudge) -> str | None:
    if row.item_type == "reminder":
        reminder = db.get(CalendarReminder, row.item_id)

        return None if reminder else "The reminder was deleted"

    if row.item_type == "job":
        return None if job_by_id(str(row.item_id)) else "The job is no longer active"

    event = db.get(CalendarEvent, row.item_id)
    if not event:
        return "The event was deleted"
    if event.status == "cancelled":
        return "The event was cancelled"

    recipient = db.scalar(
        select(CalendarEventRecipient).where(
            CalendarEventRecipient.event_id == event.event_id,
            CalendarEventRecipient.student_id == row.student_id,
        )
    )
    if not recipient or recipient.state != "active":
        return "The student is no longer in the audience"

    return None


def _quiet_until(settings, moment: datetime) -> datetime | None:
    start = settings.quiet_hours_start
    end = settings.quiet_hours_end
    local = _local(moment)
    clock = local.time()
    overnight = start > end
    inside = (clock >= start or clock < end) if overnight else (start <= clock < end)

    if not inside:
        return None

    day = local.date() + timedelta(days=1) if overnight and clock >= start else local.date()

    return to_utc(day, end)


def message_for(db: Session, row: CalendarNudge) -> str:
    if row.item_type == "reminder":
        reminder = db.get(CalendarReminder, row.item_id)

        return f"Reminder: {reminder.title}" if reminder else "A reminder you set has passed."

    if row.item_type == "job":
        job = job_by_id(str(row.item_id))
        if not job:
            return "An application window has closed."
        if row.nudge_type == DEADLINE_LAST_DAY:
            return f"Last day to apply: {job.company} {job.title}"

        days = (job.application_end_date - _local(row.scheduled_at).date()).days

        return f"{job.company} {job.title} applications close in {days} days"

    event = db.get(CalendarEvent, row.item_id)
    if not event:
        return "An event on your calendar has changed."

    where = event.venue or event.online_platform or ""
    tail = f" · {where}" if where else ""
    start = local_time(event.start_at) or ""

    if row.nudge_type == ASSESSMENT_DAY:
        end = local_time(event.end_at) or ""

        return f"Your online test is today ({start}–{end}). Check your email for the test link."

    if row.nudge_type == EVENT_HOUR_BEFORE:
        return f"{event.title} starts in 1 hour{tail}"

    return f"Reminder: {event.title} tomorrow at {start}{tail}"


def _sent_today(db: Session, student_id, day: date) -> int:
    rows = db.scalars(
        select(CalendarNudge).where(
            CalendarNudge.student_id == student_id,
            CalendarNudge.status == "sent",
            CalendarNudge.nudge_type != REMINDER_ALERT,
        )
    )

    return len([row for row in rows if row.sent_at and _local(row.sent_at).date() == day])


def run_due(db: Session, now: datetime | None = None) -> dict[str, int]:
    moment = now or _now()
    settings = settings_service.current_row(db)
    due = list(
        db.scalars(
            select(CalendarNudge)
            .where(CalendarNudge.status == "scheduled", CalendarNudge.scheduled_at <= moment)
            .order_by(CalendarNudge.scheduled_at)
        )
    )

    counts = {"sent": 0, "skipped": 0, "held": 0}

    by_student: dict[str, list[CalendarNudge]] = {}
    for row in due:
        reason = _still_relevant(db, row)
        if reason:
            row.status = "skipped"
            row.skip_reason = reason
            counts["skipped"] += 1
            continue

        skips_quiet_hours = row.nudge_type in (EVENT_HOUR_BEFORE, REMINDER_ALERT)
        held_until = None if skips_quiet_hours else _quiet_until(settings, moment)
        if held_until and held_until > moment:
            row.scheduled_at = held_until
            counts["held"] += 1
            continue

        by_student.setdefault(str(row.student_id), []).append(row)

    for student_id, rows in by_student.items():
        alerts = [row for row in rows if row.nudge_type == REMINDER_ALERT]
        counted = [row for row in rows if row.nudge_type != REMINDER_ALERT]

        for row in alerts:
            row.status = "sent"
            row.sent_at = moment
            counts["sent"] += 1

        allowed = settings.daily_nudge_limit - _sent_today(db, uuid.UUID(student_id), _local(moment).date())
        counted.sort(key=lambda entry: (PRIORITY[entry.nudge_type], entry.scheduled_at))

        for index, row in enumerate(counted):
            if index < max(allowed, 0):
                row.status = "sent"
                row.sent_at = moment
                counts["sent"] += 1
                continue

            row.status = "skipped"
            row.skip_reason = "Daily nudge limit reached"
            counts["skipped"] += 1

    db.commit()

    return counts


def sent_for(db: Session, student_id: str) -> list[CalendarNudge]:
    return list(
        db.scalars(
            select(CalendarNudge)
            .where(CalendarNudge.student_id == uuid.UUID(student_id), CalendarNudge.status == "sent")
            .order_by(CalendarNudge.sent_at.desc())
        )
    )
