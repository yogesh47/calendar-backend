"""
Who can sign in, read from the database.

This used to be a tuple of users written into the source. They live in
`calendar_user` now, so adding one, changing a role or disabling an account is
a row — not a deploy. `setup/seed_users.py` writes the original four so an
empty database still has someone to sign in as.

The row is handed on as `SignedInUser`, a frozen snapshot with its ids already
turned into strings, because that is what the services compare against.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.passwords import verify_password
from app.db.models import CalendarUser

TPO = "tpo"
STUDENT = "student"
SUPER_ADMIN = "super_admin"


@dataclass(frozen=True)
class SignedInUser:
    user_id: str
    org_id: str
    name: str
    email: str
    role: str


def to_user(row: CalendarUser) -> SignedInUser:
    return SignedInUser(
        user_id=str(row.user_id),
        org_id=str(row.org_id),
        name=row.name,
        email=row.email,
        role=row.role,
    )


def _active(statement):
    return statement.where(CalendarUser.is_active.is_(True))


def row_by_email(db: Session, email: str) -> CalendarUser | None:
    wanted = (email or "").strip().lower()
    if not wanted:
        return None

    return db.scalars(
        _active(select(CalendarUser).where(func.lower(CalendarUser.email) == wanted))
    ).first()


def find_by_email(db: Session, email: str) -> SignedInUser | None:
    row = row_by_email(db, email)

    return to_user(row) if row else None


def find_by_id(db: Session, user_id: str) -> SignedInUser | None:
    try:
        key = uuid.UUID(str(user_id))
    except (AttributeError, TypeError, ValueError):
        # A malformed id in a token is simply nobody, not a server error.
        return None

    row = db.scalars(_active(select(CalendarUser).where(CalendarUser.user_id == key))).first()

    return to_user(row) if row else None


def authenticate(db: Session, email: str, password: str) -> SignedInUser | None:
    row = row_by_email(db, email)
    if not row or not verify_password(password or "", row.password_hash):
        return None

    return to_user(row)


def students_of(db: Session, org_id: str) -> list[SignedInUser]:
    rows = db.scalars(
        _active(
            select(CalendarUser)
            .where(CalendarUser.org_id == org_id, CalendarUser.role == STUDENT)
            .order_by(CalendarUser.name)
        )
    ).all()

    return [to_user(row) for row in rows]
