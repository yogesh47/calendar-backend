"""Each user's own calendar-sync choices

Empty means the college's default from Settings.

Revision ID: b8f6d0e2a475
Revises: a7e5c9d1f364
"""

import sqlalchemy as sa
from alembic import op

revision = "b8f6d0e2a475"
down_revision = "a7e5c9d1f364"
branch_labels = None
depends_on = None

COLUMNS = (
    ("feed_past_days", sa.Integer()),
    ("feed_future_days", sa.Integer()),
    ("feed_events", sa.Boolean()),
    ("feed_deadlines", sa.Boolean()),
    ("feed_reminders", sa.Boolean()),
    ("feed_cancelled", sa.Boolean()),
)


def upgrade() -> None:
    for name, kind in COLUMNS:
        op.add_column("calendar_user", sa.Column(name, kind, nullable=True))


def downgrade() -> None:
    for name, _ in reversed(COLUMNS):
        op.drop_column("calendar_user", name)
