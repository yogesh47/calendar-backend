import logging
import uuid
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.users import students_of
from app.db.models import (
    CalendarEvent,
    CalendarEventRecipient,
    CalendarNudge,
    CalendarReminder,
    CalendarUser,
)
from app.services import settings_service
from app.services.clock import in_zone, local_date, local_time, to_utc, zone_label
from app.services.jobs import CAMPUS_JOBS, has_applied, is_open, job_by_id
from app.services.students import STUDENT_PROFILE

LOGGER = logging.getLogger("calendar.nudges")

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


def _local(moment: datetime, zone: str | None = None) -> datetime:
    return in_zone(moment, zone)


def student_zone(db: Session, student_id, org_id) -> str:
    """Where the student is: their own zone, or their org's campus time until their browser has said."""
    row = db.get(CalendarUser, uuid.UUID(str(student_id)))
    return (row.time_zone if row and row.time_zone else None) or settings_service.org_zone(db, str(org_id))


# Nudges pinned to a time of the student's day ("8 AM on test day"), not to an
# event's own instant. These follow the student when they move.
_MORNING_KINDS = (ASSESSMENT_DAY, DEADLINE_DAYS_BEFORE, DEADLINE_LAST_DAY)


def move_to_zone(db: Session, student_id, old_zone: str, new_zone: str) -> int:
    """Keep a moved student's pending morning nudges at the same wall clock in their new zone."""
    if old_zone == new_zone:
        return 0

    rows = db.scalars(
        select(CalendarNudge).where(
            CalendarNudge.student_id == uuid.UUID(str(student_id)),
            CalendarNudge.status == "scheduled",
            CalendarNudge.nudge_type.in_(_MORNING_KINDS),
        )
    ).all()
    for row in rows:
        wall = in_zone(row.scheduled_at, old_zone)
        moved = to_utc(wall.date(), wall.time(), new_zone)
        # Moving back to a zone they were in before lands on a slot that already
        # has its row (sent or skipped then); that one stands, this one goes.
        taken = db.scalar(
            select(CalendarNudge.nudge_id).where(
                CalendarNudge.student_id == row.student_id,
                CalendarNudge.nudge_type == row.nudge_type,
                CalendarNudge.item_id == row.item_id,
                CalendarNudge.scheduled_at == moved,
                CalendarNudge.nudge_id != row.nudge_id,
            )
        )
        if taken:
            db.delete(row)
        else:
            row.scheduled_at = moved
        db.flush()
    db.commit()

    return len(rows)


def _add(
    db: Session,
    org_id,
    student_id,
    nudge_type: str,
    item_type: str,
    item_id: str,
    when: datetime,
    was_due: set[tuple[str, str]] | None = None,
) -> None:
    # A moment already past is not scheduled — unless this very nudge was due
    # and waiting for the runner when the item was edited. Dropping it then
    # would lose it for good, so it goes back in as due now.
    if when <= _now():
        if not was_due or (str(student_id), nudge_type) not in was_due:
            return
        when = _now()

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


# The student applied, so drop their pending nudges for that job.
def drop_for_job(db: Session, job_id: str, student_id: str) -> None:
    try:
        db.query(CalendarNudge).filter(
            CalendarNudge.item_id == uuid.UUID(job_id),
            CalendarNudge.student_id == uuid.UUID(student_id),
            CalendarNudge.status == "scheduled",
        ).delete()
        db.commit()
    except Exception as err:
        LOGGER.error("drop_for_job failed: %s", err)
        db.rollback()
        raise


def _drop_scheduled(db: Session, item_id) -> set[tuple[str, str]]:
    """Drops an item's pending nudges and says which were already due but not yet sent."""
    pending = db.query(CalendarNudge).filter(
        CalendarNudge.item_id == item_id,
        CalendarNudge.status == "scheduled",
    )
    was_due = {(str(row.student_id), row.nudge_type) for row in pending if row.scheduled_at <= _now()}
    pending.delete()

    return was_due


# Stages the nudges for an event and does NOT commit: the caller owns the
# transaction, so the event and its nudges are written together or not at all.
def schedule_for_event(db: Session, event: CalendarEvent) -> None:
    was_due = _drop_scheduled(db, event.event_id)

    if event.status != "published":
        return

    settings = settings_service.current_row(db, str(event.org_id))
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
                was_due,
            )
            _add(
                db,
                event.org_id,
                recipient.student_id,
                EVENT_HOUR_BEFORE,
                "event",
                str(event.event_id),
                event.start_at - timedelta(hours=settings.event_reminder_hours_before),
                was_due,
            )

        if event.event_type == "online_assessment":
            # 8 a.m. on the test's day — the student's own morning, wherever they are.
            zone = student_zone(db, recipient.student_id, event.org_id)
            test_day = local_date(event.start_at, zone) or event.event_date
            _add(
                db,
                event.org_id,
                recipient.student_id,
                ASSESSMENT_DAY,
                "event",
                str(event.event_id),
                to_utc(test_day, ASSESSMENT_HOUR, zone),
                was_due,
            )


def alert_at(reminder) -> datetime | None:
    if reminder.remind_before in (None, "none"):
        return None

    # In the zone the reminder was typed in — its owner's own.
    zone = getattr(reminder, "time_zone", None)
    if reminder.reminder_time:
        moment = to_utc(reminder.reminder_date, reminder.reminder_time, zone)
        return moment - REMIND_BEFORE_OFFSET.get(reminder.remind_before, timedelta(0))

    return to_utc(reminder.reminder_date, ALL_DAY_ALERT_HOUR, zone)


# Same contract as schedule_for_event: stages only, the caller commits.
def schedule_for_reminder(db: Session, reminder) -> None:
    was_due = _drop_scheduled(db, reminder.reminder_id)
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
            was_due,
        )


def _reschedule(db: Session, org_id, student_id, nudge_type: str, item_id: str, when: datetime) -> None:
    """
    Deadline nudges are worked out afresh every tick. A pending one whose time
    no longer matches (the zone or the settings changed) is replaced, so a
    student never gets the same nudge twice at two different times.
    """
    stale = db.scalars(
        select(CalendarNudge).where(
            CalendarNudge.student_id == uuid.UUID(str(student_id)),
            CalendarNudge.nudge_type == nudge_type,
            CalendarNudge.item_id == uuid.UUID(item_id),
            CalendarNudge.status == "scheduled",
            CalendarNudge.scheduled_at != when,
        )
    ).all()
    for row in stale:
        db.delete(row)
    if stale:
        db.flush()

    _add(db, org_id, student_id, nudge_type, "job", item_id, when)


def move_org_to_zone(db: Session, org_id: str, old_zone: str, new_zone: str) -> int:
    """The college's zone changed: students who have no zone of their own move with it."""
    moved = 0
    for student in students_of(db, org_id):
        if not student.time_zone:
            moved += move_to_zone(db, student.user_id, old_zone, new_zone)

    return moved


def schedule_deadlines(db: Session, org_id: str) -> None:
    try:
        settings = settings_service.current_row(db, org_id)
        students = students_of(db, org_id)

        for job in CAMPUS_JOBS:
            if not is_open(job) or STUDENT_PROFILE["department"] not in job.departments:
                continue

            for student in students:
                if has_applied(job.job_id, student.user_id):
                    continue

                # 9 a.m. in the student's own zone.
                zone = student.time_zone or settings.time_zone
                _reschedule(
                    db,
                    org_id,
                    student.user_id,
                    DEADLINE_DAYS_BEFORE,
                    job.job_id,
                    to_utc(job.application_end_date - timedelta(days=settings.deadline_reminder_days_before), DEADLINE_HOUR, zone),
                )

                if settings.deadline_reminder_same_day:
                    _reschedule(
                        db,
                        org_id,
                        student.user_id,
                        DEADLINE_LAST_DAY,
                        job.job_id,
                        to_utc(job.application_end_date, DEADLINE_HOUR, zone),
                    )

        db.commit()
    except Exception as err:
        LOGGER.error("schedule_deadlines failed: %s", err)
        db.rollback()
        raise


def _still_relevant(db: Session, row: CalendarNudge) -> str | None:
    if row.item_type == "reminder":
        reminder = db.get(CalendarReminder, row.item_id)
        if not reminder:
            return "The reminder was deleted"

        if reminder.linked_type == "event" and reminder.linked_id:
            linked = db.get(CalendarEvent, reminder.linked_id)
            if linked and linked.status == "cancelled":
                return "The linked event was cancelled"

        return None

    if row.item_type == "job":
        job = job_by_id(str(row.item_id))
        if not job or not is_open(job):
            return "The job is no longer active"

        if has_applied(job.job_id, str(row.student_id)):
            return "The student has already applied"

        return None

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


def _quiet_until(settings, moment: datetime, zone: str | None = None) -> datetime | None:
    """When the night ends for this student, if `moment` falls in their quiet hours."""
    start = settings.quiet_hours_start
    end = settings.quiet_hours_end
    local = _local(moment, zone)
    clock = local.time()
    overnight = start > end
    inside = (clock >= start or clock < end) if overnight else (start <= clock < end)

    if not inside:
        return None

    day = local.date() + timedelta(days=1) if overnight and clock >= start else local.date()

    return to_utc(day, end, zone)


# The 1-hour reminder is only exempt from quiet hours when the event itself starts in them.
def _starts_in_quiet_hours(db: Session, settings, row: CalendarNudge, zone: str | None = None) -> bool:
    event = db.get(CalendarEvent, row.item_id) if row.item_type == "event" else None
    if not event or not event.start_at:
        return False

    return _quiet_until(settings, event.start_at, zone) is not None


def message_for(db: Session, row: CalendarNudge, zone: str | None = None) -> str:
    """The nudge's words, with times in `zone` — the reader's own."""
    zone = zone or student_zone(db, row.student_id, row.org_id)
    if row.item_type == "reminder":
        reminder = db.get(CalendarReminder, row.item_id)

        return f"Reminder: {reminder.title}" if reminder else "A reminder you set has passed."

    if row.item_type == "job":
        job = job_by_id(str(row.item_id))
        if not job:
            return "An application window has closed."
        if row.nudge_type == DEADLINE_LAST_DAY:
            return f"Last day to apply: {job.company} {job.title}"

        days = (job.application_end_date - _local(row.scheduled_at, zone).date()).days

        return f"{job.company} {job.title} applications close in {days} days"

    event = db.get(CalendarEvent, row.item_id)
    if not event:
        return "An event on your calendar has changed."

    where = event.venue or event.online_platform or ""
    tail = f" · {where}" if where else ""
    label = f" {zone_label(event.start_at, zone)}" if event.start_at else ""
    start = (local_time(event.start_at, zone) or "") + label

    if row.nudge_type == ASSESSMENT_DAY:
        end = local_time(event.end_at, zone) or ""

        return f"Your online test is today ({local_time(event.start_at, zone)}–{end}{label}). Check your email for the test link."

    # A deadline does not start, it closes.
    if row.nudge_type == EVENT_HOUR_BEFORE:
        if event.event_type == "deadline":
            return f"{event.title} closes in 1 hour"
        return f"{event.title} starts in 1 hour{tail}"

    if event.event_type == "deadline":
        return f"{event.title} closes tomorrow at {start}"

    return f"Reminder: {event.title} tomorrow at {start}{tail}"


def _sent_today(db: Session, student_id, day: date, zone: str | None = None) -> int:
    rows = db.scalars(
        select(CalendarNudge).where(
            CalendarNudge.student_id == student_id,
            CalendarNudge.status == "sent",
            CalendarNudge.nudge_type != REMINDER_ALERT,
        )
    )

    return len([row for row in rows if row.sent_at and _local(row.sent_at, zone).date() == day])


def run_due(db: Session, now: datetime | None = None) -> dict[str, int]:
    try:
        moment = now or _now()
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

            # Each org's own settings, and the student's own night.
            settings = settings_service.current_row(db, str(row.org_id))
            zone = student_zone(db, row.student_id, row.org_id)
            skips_quiet_hours = row.nudge_type == REMINDER_ALERT or (
                row.nudge_type == EVENT_HOUR_BEFORE and _starts_in_quiet_hours(db, settings, row, zone)
            )
            held_until = None if skips_quiet_hours else _quiet_until(settings, moment, zone)
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

            settings = settings_service.current_row(db, str(rows[0].org_id))
            zone = student_zone(db, student_id, rows[0].org_id)
            # "Today" is the student's today.
            allowed = settings.daily_nudge_limit - _sent_today(db, uuid.UUID(student_id), _local(moment, zone).date(), zone)
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
    except Exception as err:
        LOGGER.error("run_due failed: %s", err)
        db.rollback()
        raise


def sent_for(db: Session, student_id: str) -> list[CalendarNudge]:
    return list(
        db.scalars(
            select(CalendarNudge)
            .where(CalendarNudge.student_id == uuid.UUID(student_id), CalendarNudge.status == "sent")
            .order_by(CalendarNudge.sent_at.desc())
        )
    )
