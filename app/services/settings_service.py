import logging
import uuid
from datetime import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.users import SignedInUser
from app.db.models import CalendarSettings
from app.models.settings_model import SettingsIn, SettingsOut
from app.services.clock import DEFAULT_ZONE

LOGGER = logging.getLogger("calendar.settings")

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
        time_zone=row.time_zone,
    )


def current_row(db: Session, org_id: str | None = None) -> CalendarSettings:
    """
    The org's own settings. An org that has none yet starts from the template
    row (the one without an org) — or from the defaults — and gets its own copy.
    """
    try:
        key = uuid.UUID(str(org_id)) if org_id else None
        row = db.scalars(select(CalendarSettings).where(CalendarSettings.org_id == key)).first() if key else None
        if row:
            return row

        template = db.scalars(select(CalendarSettings).where(CalendarSettings.org_id.is_(None))).first()
        if not key and template:
            return template

        values = (
            {name: getattr(template, name) for name in [*DEFAULTS, "time_zone"]}
            if template
            else {**DEFAULTS, "time_zone": DEFAULT_ZONE}
        )
        row = CalendarSettings(org_id=key, **values)
        db.add(row)
        db.commit()
        db.refresh(row)

        return row
    except Exception as err:
        LOGGER.error("current_row failed: %s", err)
        db.rollback()
        raise


def org_zone(db: Session, org_id: str | None) -> str:
    """The org's campus time zone."""
    return current_row(db, org_id).time_zone or DEFAULT_ZONE


def detect_org_zone(db: Session, org_id: str, zone: str) -> str | None:
    """
    The first staff browser to sign in sets its org's campus time; after that
    only an admin changes it. Returns the zone it replaced, if it changed.
    """
    row = current_row(db, org_id)
    if row.time_zone_source != "default":
        return None

    old = row.time_zone
    row.time_zone = zone
    row.time_zone_source = "detected"
    db.commit()

    return old if old != zone else None


def read_settings(db: Session, org_id: str | None = None) -> SettingsOut:
    return settings_out(current_row(db, org_id))


def save_settings(db: Session, user: SignedInUser, payload: SettingsIn) -> SettingsOut:
    try:
        row = current_row(db, user.org_id)
        if payload.time_zone and payload.time_zone != row.time_zone:
            row.time_zone = payload.time_zone
            row.time_zone_source = "admin"
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
    except Exception as err:
        LOGGER.error("save_settings failed: %s", err)
        db.rollback()
        raise
