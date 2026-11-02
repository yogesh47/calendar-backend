"""Sync range: "All" and a fixed date at either end

A user's calendar-sync feed could only reach a number of days back and ahead.
Each end can now also be "all" (as far as the feed goes) or a fixed date.

Revision ID: c9e1b3d5f7a2
Revises: a1c4e7f2b905
"""

import sqlalchemy as sa
from alembic import op

revision = "c9e1b3d5f7a2"
down_revision = "a1c4e7f2b905"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("calendar_user", sa.Column("feed_past_mode", sa.String(length=10), nullable=True))
    op.add_column("calendar_user", sa.Column("feed_past_from", sa.Date(), nullable=True))
    op.add_column("calendar_user", sa.Column("feed_future_mode", sa.String(length=10), nullable=True))
    op.add_column("calendar_user", sa.Column("feed_future_to", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("calendar_user", "feed_future_to")
    op.drop_column("calendar_user", "feed_future_mode")
    op.drop_column("calendar_user", "feed_past_from")
    op.drop_column("calendar_user", "feed_past_mode")
