"""How an org's time zone was set

"default" until the first staff browser signs in ("detected") or an admin
chooses one in Settings ("admin"). Only "default" is replaced automatically.

Revision ID: e5c3f7a9b142
Revises: d4b2e6f8a031
"""

import sqlalchemy as sa
from alembic import op

revision = "e5c3f7a9b142"
down_revision = "d4b2e6f8a031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "calendar_settings",
        sa.Column("time_zone_source", sa.String(20), nullable=False, server_default="default"),
    )


def downgrade() -> None:
    op.drop_column("calendar_settings", "time_zone_source")
