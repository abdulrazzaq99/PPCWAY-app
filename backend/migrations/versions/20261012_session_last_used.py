"""When a session was last used, so it can roll forward while it is.

A fixed thirty days from sign-in signs out somebody who has been here every day,
which is the kind of thing nobody reports as a bug and everybody resents.

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "b8c9d0e1f2a3"
down_revision = "a7b8c9d0e1f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("account_session") as batch:
        batch.add_column(sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True))
    # Existing sessions have been used at least once: when they were made.
    op.execute("UPDATE account_session SET last_used_at = created_at WHERE last_used_at IS NULL")


def downgrade() -> None:
    with op.batch_alter_table("account_session") as batch:
        batch.drop_column("last_used_at")
