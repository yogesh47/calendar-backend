from sqlalchemy import UniqueConstraint

from app.db.models import columns
from app.db.session import Base


class CalendarPushDevice(Base):
    __tablename__ = "calendar_push_device"
    __table_args__ = (UniqueConstraint("token", name="uq_calendar_push_device_token"),)

    device_id = columns.primary_key()
    org_id = columns.required_id(index=True)
    user_id = columns.required_id(index=True)
    token = columns.text(255, nullable=False)
    platform = columns.text(20, nullable=False)
    created_at = columns.created_at()
    last_seen_at = columns.updated_at()
