"""The trade a business is in, so its searches can be looked up.

Keyword Planner needs a phrase people would type. "Alpha Plumbing" is a name;
"plumber" is a search. The form already asks, and now the answer is kept.

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "a7b8c9d0e1f2"
down_revision = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("audit_request") as batch:
        batch.add_column(sa.Column("trade", sa.String(120), nullable=False, server_default=""))


def downgrade() -> None:
    with op.batch_alter_table("audit_request") as batch:
        batch.drop_column("trade")
