"""Repeating reminders

A repeating reminder is written as one row per date, like a repeating event:
`series_id` ties them together and `recurrence` keeps the rule.

Revision ID: c3a91d5e7f20
Revises: b7e2f0c4a913
"""

import sqlalchemy as sa
from alembic import op

revision = "c3a91d5e7f20"
down_revision = "b7e2f0c4a913"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("calendar_reminder", sa.Column("series_id", sa.UUID(), nullable=True))
    op.add_column("calendar_reminder", sa.Column("recurrence", sa.String(length=80), nullable=True))
    op.create_index("ix_calendar_reminder_series", "calendar_reminder", ["series_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_calendar_reminder_series", table_name="calendar_reminder")
    op.drop_column("calendar_reminder", "recurrence")
    op.drop_column("calendar_reminder", "series_id")
