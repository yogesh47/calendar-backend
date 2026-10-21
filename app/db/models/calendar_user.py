from sqlalchemy import UniqueConstraint

from app.db.models import columns
from app.db.session import Base


class CalendarUser(Base):
    """
    Who can sign in. This replaced a tuple of hardcoded users in the source, so
    adding or disabling someone is a row rather than a deploy.

    `password_hash` holds a PBKDF2 digest, never the password itself — see
    app/auth/passwords.py.
    """

    __tablename__ = "calendar_user"
    __table_args__ = (UniqueConstraint("email", name="uq_calendar_user_email"),)

    user_id = columns.primary_key()
    org_id = columns.required_id(index=True)
    name = columns.text(120, nullable=False)
    email = columns.text(160, nullable=False)
    role = columns.text(20, nullable=False)
    password_hash = columns.text(255, nullable=False)
    is_active = columns.flag(default=True)
    created_at = columns.created_at()
    updated_at = columns.updated_at()
