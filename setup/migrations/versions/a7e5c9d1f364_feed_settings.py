"""Calendar-sync feed settings per org

Days back and ahead of today the .ics feed carries, and whether cancelled
events are included (titled "Cancelled: …").

Revision ID: a7e5c9d1f364
Revises: f6d4a8b0c253
"""

import sqlalchemy as sa
from alembic import op

revision = "a7e5c9d1f364"
down_revision = "f6d4a8b0c253"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "calendar_settings",
        sa.Column("feed_past_days", sa.Integer(), nullable=False, server_default="30"),
    )
    op.add_column(
        "calendar_settings",
        sa.Column(
            "feed_future_days", sa.Integer(), nullable=False, server_default="365"
        ),
    )
    op.add_column(
        "calendar_settings",
        sa.Column(
            "feed_show_cancelled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )


def downgrade() -> None:
    op.drop_column("calendar_settings", "feed_show_cancelled")
    op.drop_column("calendar_settings", "feed_future_days")
    op.drop_column("calendar_settings", "feed_past_days")
