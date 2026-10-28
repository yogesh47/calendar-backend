"""Store current zone names, not the old ones browsers report

Chrome in India reports "Asia/Calcutta". The API now stores "Asia/Kolkata"
(see clock.ZONE_ALIASES); this rewrites rows saved before that.

Revision ID: f6d4a8b0c253
Revises: e5c3f7a9b142
"""

from alembic import op

from app.services.clock import ZONE_ALIASES

revision = "f6d4a8b0c253"
down_revision = "e5c3f7a9b142"
branch_labels = None
depends_on = None

TABLES = ("calendar_settings", "calendar_user", "calendar_event", "calendar_reminder")


def upgrade() -> None:
    for table in TABLES:
        for old, new in ZONE_ALIASES.items():
            op.execute(f"UPDATE {table} SET time_zone = '{new}' WHERE time_zone = '{old}'")


def downgrade() -> None:
    # The old names meant the same zones; nothing to undo.
    pass
