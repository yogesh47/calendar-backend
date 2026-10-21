"""Generate every uuid primary key in the database too

The ids were minted only in Python (`default=uuid.uuid4`), so an ORM insert got
one and a hand-written `INSERT` did not — it failed on NOT NULL instead. Adding
the server default puts the rule where the column is, so both routes work.

gen_random_uuid() is built into Postgres 13 and later; no extension is needed.

Revision ID: 9c1a7d4e2b30
Revises: 188f4317264a
"""

from alembic import op

revision = "9c1a7d4e2b30"
down_revision = "188f4317264a"
branch_labels = None
depends_on = None

# Every table whose primary key is a uuid, with the column that holds it.
PRIMARY_KEYS = (
    ("calendar_event", "event_id"),
    ("calendar_event_audience", "audience_id"),
    ("calendar_event_recipient", "recipient_id"),
    ("calendar_nudge", "nudge_id"),
    ("calendar_push_device", "device_id"),
    ("calendar_reminder", "reminder_id"),
    ("calendar_settings", "settings_id"),
    ("calendar_user", "user_id"),
)


def upgrade() -> None:
    for table, column in PRIMARY_KEYS:
        op.execute(f'ALTER TABLE {table} ALTER COLUMN {column} SET DEFAULT gen_random_uuid()')


def downgrade() -> None:
    for table, column in PRIMARY_KEYS:
        op.execute(f'ALTER TABLE {table} ALTER COLUMN {column} DROP DEFAULT')
