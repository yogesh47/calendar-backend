"""Time zones: per org, per user, per event and reminder

Orgs keep their own campus time (many may share one); users keep where they
are; events and reminders keep the zone their times were typed in. Existing
rows were all typed in the one zone the service used until now.

Revision ID: d4b2e6f8a031
Revises: c3a91d5e7f20
"""

import sqlalchemy as sa
from alembic import op

revision = "d4b2e6f8a031"
down_revision = "c3a91d5e7f20"
branch_labels = None
depends_on = None

DEFAULT = "Asia/Kolkata"


def upgrade() -> None:
    op.add_column("calendar_settings", sa.Column("org_id", sa.UUID(), nullable=True))
    op.add_column("calendar_settings", sa.Column("time_zone", sa.String(64), nullable=False, server_default=DEFAULT))
    op.create_index("ix_calendar_settings_org", "calendar_settings", ["org_id"], unique=True)
    op.add_column("calendar_user", sa.Column("time_zone", sa.String(64), nullable=True))
    op.add_column("calendar_event", sa.Column("time_zone", sa.String(64), nullable=True))
    op.add_column("calendar_reminder", sa.Column("time_zone", sa.String(64), nullable=True))
    op.execute(f"UPDATE calendar_event SET time_zone = '{DEFAULT}' WHERE time_zone IS NULL")
    op.execute(f"UPDATE calendar_reminder SET time_zone = '{DEFAULT}' WHERE time_zone IS NULL")


def downgrade() -> None:
    op.drop_column("calendar_reminder", "time_zone")
    op.drop_column("calendar_event", "time_zone")
    op.drop_column("calendar_user", "time_zone")
    op.drop_index("ix_calendar_settings_org", table_name="calendar_settings")
    op.drop_column("calendar_settings", "time_zone")
    op.drop_column("calendar_settings", "org_id")
