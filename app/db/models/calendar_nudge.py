from sqlalchemy import Index, UniqueConstraint

from app.db.models import columns
from app.db.session import Base


class CalendarNudge(Base):
    __tablename__ = "calendar_nudge"
    __table_args__ = (
        UniqueConstraint(
            "student_id",
            "nudge_type",
            "item_id",
            "scheduled_at",
            name="uq_calendar_nudge_no_double_send",
        ),
        Index("ix_calendar_nudge_due", "status", "scheduled_at"),
    )

    nudge_id = columns.primary_key()
    org_id = columns.required_id(index=True)
    student_id = columns.required_id(index=True)
    nudge_type = columns.text(40, nullable=False)
    item_type = columns.text(20, nullable=False)
    item_id = columns.required_id()
    scheduled_at = columns.moment(nullable=False, index=True)
    sent_at = columns.moment()
    status = columns.text(20, nullable=False, default="scheduled")
    skip_reason = columns.text(200)
