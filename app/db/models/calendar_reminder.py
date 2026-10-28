from sqlalchemy import Index

from app.db.models import columns
from app.db.session import Base


class CalendarReminder(Base):
    __tablename__ = "calendar_reminder"
    __table_args__ = (
        Index("ix_calendar_reminder_owner_date", "owner_id", "reminder_date"),
        Index("ix_calendar_reminder_series", "series_id"),
    )

    reminder_id = columns.primary_key()
    org_id = columns.required_id(index=True)
    owner_id = columns.required_id(index=True)
    owner_role = columns.text(20, nullable=False)
    title = columns.text(120, nullable=False)
    reminder_date = columns.day()
    reminder_time = columns.clock()
    remind_before = columns.text(20, nullable=False, default="none")
    alert_at = columns.moment()
    note = columns.text(500)
    linked_type = columns.text(20)
    linked_id = columns.optional_id()
    # A repeating reminder is one row per date, like a repeating event: they
    # share `series_id` and keep the rule they came from.
    series_id = columns.optional_id()
    recurrence = columns.text(80)
    # The zone its time was typed in — the owner's own, wherever they are.
    time_zone = columns.text(64)
    created_at = columns.created_at()
    updated_at = columns.updated_at()
