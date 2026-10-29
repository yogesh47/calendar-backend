from app.db.models import columns
from app.db.session import Base


class CalendarSettings(Base):
    __tablename__ = "calendar_settings"

    settings_id = columns.primary_key()
    # One row per org. A row without an org is the template new orgs start from.
    org_id = columns.optional_id()
    # The org's campus time — the zone its events are typed in. Orgs may share one.
    time_zone = columns.text(64, nullable=False, default="Asia/Kolkata")
    # How the zone was set: "default" (never), "detected" (the first staff
    # browser to sign in) or "admin" (chosen in Settings). Only "default" is
    # replaced automatically, so a travelling TPO never moves their campus.
    time_zone_source = columns.text(20, nullable=False, default="default")
    event_reminder_days_before = columns.count(default=1)
    event_reminder_hours_before = columns.count(default=1)
    deadline_reminder_days_before = columns.count(default=2)
    deadline_reminder_same_day = columns.flag(default=True)
    daily_nudge_limit = columns.count(default=3)
    quiet_hours_start = columns.clock(nullable=False)
    quiet_hours_end = columns.clock(nullable=False)
    # What the calendar-sync (.ics) feed carries: days back and ahead of today, and cancelled events.
    feed_past_days = columns.count(default=30)
    feed_future_days = columns.count(default=365)
    feed_show_cancelled = columns.flag(default=True)
    updated_by = columns.optional_id()
    updated_at = columns.updated_at()
