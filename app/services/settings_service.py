import uuid
from datetime import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.users import HardcodedUser
from app.db.models import CalendarSettings
from app.models.settings_model import SettingsIn, SettingsOut

DEFAULTS = {
    "event_reminder_days_before": 1,
    "event_reminder_hours_before": 1,
    "deadline_reminder_days_before": 2,
    "deadline_reminder_same_day": True,
    "daily_nudge_limit": 3,
    "quiet_hours_start": time(22, 0),
    "quiet_hours_end": time(7, 0),
}


def settings_out(row: CalendarSettings) -> SettingsOut:
    return SettingsOut(
        event_reminder_days_before=row.event_reminder_days_before,
        event_reminder_hours_before=row.event_reminder_hours_before,
        deadline_reminder_days_before=row.deadline_reminder_days_before,
        deadline_reminder_same_day=row.deadline_reminder_same_day,
        daily_nudge_limit=row.daily_nudge_limit,
        quiet_hours_start=row.quiet_hours_start.strftime("%H:%M"),
        quiet_hours_end=row.quiet_hours_end.strftime("%H:%M"),
        updated_at=row.updated_at.isoformat() if row.updated_at else None,
    )


def current_row(db: Session) -> CalendarSettings:
    row = db.scalars(select(CalendarSettings)).first()
    if row:
        return row

    row = CalendarSettings(**DEFAULTS)
    db.add(row)
    db.commit()
    db.refresh(row)

    return row


def read_settings(db: Session) -> SettingsOut:
    return settings_out(current_row(db))


def save_settings(db: Session, user: HardcodedUser, payload: SettingsIn) -> SettingsOut:
    row = current_row(db)
    row.event_reminder_days_before = payload.event_reminder_days_before
    row.event_reminder_hours_before = payload.event_reminder_hours_before
    row.deadline_reminder_days_before = payload.deadline_reminder_days_before
    row.deadline_reminder_same_day = payload.deadline_reminder_same_day
    row.daily_nudge_limit = payload.daily_nudge_limit
    row.quiet_hours_start = payload.quiet_hours_start
    row.quiet_hours_end = payload.quiet_hours_end
    row.updated_by = uuid.UUID(user.user_id)
    db.commit()
    db.refresh(row)

    return settings_out(row)
