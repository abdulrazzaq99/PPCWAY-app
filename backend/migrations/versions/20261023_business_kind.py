"""What kind of business this is, and whether the person chose it.

Revision ID: b0c1d2e3f4a5
Revises: a9b0c1d2e3f4
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "b0c1d2e3f4a5"
down_revision = "a9b0c1d2e3f4"
branch_labels = None
depends_on = None

COLUMNS = [
    sa.Column("kind", sa.String(20), nullable=False, server_default=""),
    sa.Column("kind_is_theirs", sa.Boolean(), nullable=False, server_default=sa.false()),
]


def upgrade() -> None:
    with op.batch_alter_table("audit_request") as batch:
        for column in COLUMNS:
            batch.add_column(column)


def downgrade() -> None:
    with op.batch_alter_table("audit_request") as batch:
        for column in COLUMNS:
            batch.drop_column(column.name)
