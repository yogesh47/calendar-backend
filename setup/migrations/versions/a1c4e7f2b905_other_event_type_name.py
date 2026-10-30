"""The name of an "other" event

An event of type "other" carries the TPO's own name for what it is
("Alumni Meet"), so students see more than "Other".

Revision ID: a1c4e7f2b905
Revises: b8f6d0e2a475
"""

import sqlalchemy as sa
from alembic import op

revision = "a1c4e7f2b905"
down_revision = "b8f6d0e2a475"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("calendar_event", sa.Column("other_type", sa.String(length=80), nullable=True))


def downgrade() -> None:
    op.drop_column("calendar_event", "other_type")
