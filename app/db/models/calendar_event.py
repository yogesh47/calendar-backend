from sqlalchemy import Index

from app.db.models import columns
from app.db.session import Base


class CalendarEvent(Base):
    __tablename__ = "calendar_event"
    __table_args__ = (
        Index("ix_calendar_event_org_date", "org_id", "event_date"),
        Index("ix_calendar_event_org_status", "org_id", "status"),
    )

    event_id = columns.primary_key()
    org_id = columns.required_id(index=True)
    event_type = columns.text(40, nullable=False)
    title = columns.text(120, nullable=False)
    company_id = columns.optional_id()
    event_date = columns.day()
    start_at = columns.moment()
    end_at = columns.moment()
    mode = columns.text(20)
    venue = columns.text(200)
    online_platform = columns.text(200)
    description = columns.long_text()
    linked_job_kind = columns.text(20)
    linked_job_id = columns.optional_id()
    linked_job_url = columns.text(2048)
    linked_job_title = columns.text(200)
    status = columns.text(20, nullable=False, default="published")
    cancel_reason = columns.text(40)
    cancel_note = columns.text(200)
    cancelled_by = columns.optional_id()
    cancelled_at = columns.moment()
    created_by = columns.required_id()
    created_at = columns.created_at()
    updated_at = columns.updated_at()
