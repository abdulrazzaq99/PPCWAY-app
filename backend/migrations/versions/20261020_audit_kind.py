"""Whether a run was asked for or happened on the clock.

The audit becomes a living tool in week two: it re-runs on a schedule, and the
history chart marks where fixes landed. A reading from a scheduled run and one
somebody started by hand are both readings, but a chart that cannot tell them
apart cannot explain a gap in the line.

Revision ID: e7f8a9b0c1d2
Revises: d6e7f8a9b0c1
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "e7f8a9b0c1d2"
down_revision = "d6e7f8a9b0c1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("audit_run") as batch:
        batch.add_column(sa.Column("kind", sa.String(12), nullable=False, server_default="asked"))


def downgrade() -> None:
    with op.batch_alter_table("audit_run") as batch:
        batch.drop_column("kind")
