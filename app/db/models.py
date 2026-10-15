import uuid

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID

from app.db.session import Base


class CalendarEvent(Base):
    __tablename__ = "calendar_event"
    __table_args__ = (
        Index("ix_calendar_event_org_date", "org_id", "event_date"),
        Index("ix_calendar_event_org_status", "org_id", "status"),
    )

    event_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    event_type = Column(String(40), nullable=False)
    title = Column(String(120), nullable=False)
    company_id = Column(UUID(as_uuid=True), nullable=True)
    event_date = Column(Date, nullable=False)
    start_at = Column(DateTime(timezone=True), nullable=True)
    end_at = Column(DateTime(timezone=True), nullable=True)
    is_all_day = Column(Boolean, nullable=False, default=False)
    mode = Column(String(20), nullable=True)
    venue = Column(String(200), nullable=True)
    online_platform = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)
    linked_job_kind = Column(String(20), nullable=True)
    linked_job_id = Column(UUID(as_uuid=True), nullable=True)
    linked_job_url = Column(String(2048), nullable=True)
    linked_job_title = Column(String(200), nullable=True)
    status = Column(String(20), nullable=False, default="published")
    cancel_reason = Column(String(40), nullable=True)
    cancel_note = Column(String(200), nullable=True)
    cancelled_by = Column(UUID(as_uuid=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    notified_count = Column(Integer, nullable=False, default=0)
    created_by = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class CalendarEventAudience(Base):
    __tablename__ = "calendar_event_audience"

    audience_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(
        UUID(as_uuid=True),
        ForeignKey("calendar_event.event_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    opportunity_type = Column(String(20), nullable=False)
    courses = Column(ARRAY(String), nullable=False)
    batches = Column(ARRAY(Integer), nullable=False)
    departments = Column(ARRAY(String), nullable=False)


class CalendarEventRecipient(Base):
    __tablename__ = "calendar_event_recipient"
    __table_args__ = (
        UniqueConstraint("event_id", "student_id", name="uq_calendar_recipient_event_student"),
        Index("ix_calendar_recipient_student", "org_id", "student_id"),
    )

    recipient_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    event_id = Column(
        UUID(as_uuid=True),
        ForeignKey("calendar_event.event_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    state = Column(String(20), nullable=False, default="active")
    removed_reason = Column(String(200), nullable=True)
    seen_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class CalendarReminder(Base):
    __tablename__ = "calendar_reminder"
    __table_args__ = (Index("ix_calendar_reminder_owner_date", "owner_id", "reminder_date"),)

    reminder_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    owner_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    owner_role = Column(String(20), nullable=False)
    title = Column(String(120), nullable=False)
    reminder_date = Column(Date, nullable=False)
    reminder_time = Column(Time, nullable=True)
    remind_before = Column(String(20), nullable=False, default="none")
    alert_at = Column(DateTime(timezone=True), nullable=True)
    note = Column(String(500), nullable=True)
    linked_type = Column(String(20), nullable=True)
    linked_id = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


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

    nudge_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    student_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    nudge_type = Column(String(40), nullable=False)
    item_type = Column(String(20), nullable=False)
    item_id = Column(UUID(as_uuid=True), nullable=False)
    scheduled_at = Column(DateTime(timezone=True), nullable=False, index=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), nullable=False, default="scheduled")
    skip_reason = Column(String(200), nullable=True)


class CalendarSettings(Base):
    __tablename__ = "calendar_settings"

    settings_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_reminder_days_before = Column(Integer, nullable=False, default=1)
    event_reminder_hours_before = Column(Integer, nullable=False, default=1)
    deadline_reminder_days_before = Column(Integer, nullable=False, default=2)
    deadline_reminder_same_day = Column(Boolean, nullable=False, default=True)
    daily_nudge_limit = Column(Integer, nullable=False, default=3)
    quiet_hours_start = Column(Time, nullable=False)
    quiet_hours_end = Column(Time, nullable=False)
    updated_by = Column(UUID(as_uuid=True), nullable=True)
    updated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
