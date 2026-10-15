from app.db.models import columns
from app.db.session import Base


class CalendarSettings(Base):
    __tablename__ = "calendar_settings"

    settings_id = columns.primary_key()
    event_reminder_days_before = columns.count(default=1)
    event_reminder_hours_before = columns.count(default=1)
    deadline_reminder_days_before = columns.count(default=2)
    deadline_reminder_same_day = columns.flag(default=True)
    daily_nudge_limit = columns.count(default=3)
    quiet_hours_start = columns.clock(nullable=False)
    quiet_hours_end = columns.clock(nullable=False)
    updated_by = columns.optional_id()
    updated_at = columns.updated_at()
