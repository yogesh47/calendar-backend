"""Recurring events and an image per event

A recurring event is written as one row per occurrence; `series_id` ties them
together and `recurrence` keeps the rule they were made from. `image_url` is the
path of an image uploaded through /calendar/images.

Revision ID: b7e2f0c4a913
Revises: 9c1a7d4e2b30
"""

import sqlalchemy as sa
from alembic import op

revision = "b7e2f0c4a913"
down_revision = "9c1a7d4e2b30"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("calendar_event", sa.Column("series_id", sa.UUID(), nullable=True))
    op.add_column("calendar_event", sa.Column("recurrence", sa.String(length=80), nullable=True))
    op.add_column("calendar_event", sa.Column("image_url", sa.String(length=300), nullable=True))
    op.create_index("ix_calendar_event_series", "calendar_event", ["series_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_calendar_event_series", table_name="calendar_event")
    op.drop_column("calendar_event", "image_url")
    op.drop_column("calendar_event", "recurrence")
    op.drop_column("calendar_event", "series_id")
