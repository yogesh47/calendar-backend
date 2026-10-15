from sqlalchemy import Index, UniqueConstraint

from app.db.models import columns
from app.db.session import Base


class CalendarEventRecipient(Base):
    __tablename__ = "calendar_event_recipient"
    __table_args__ = (
        UniqueConstraint("event_id", "student_id", name="uq_calendar_recipient_event_student"),
        Index("ix_calendar_recipient_student", "org_id", "student_id"),
    )

    recipient_id = columns.primary_key()
    org_id = columns.required_id(index=True)
    event_id = columns.event_id(index=True)
    student_id = columns.required_id(index=True)
    state = columns.text(20, nullable=False, default="active")
    removed_reason = columns.text(200)
    seen_at = columns.moment()
    created_at = columns.created_at()
