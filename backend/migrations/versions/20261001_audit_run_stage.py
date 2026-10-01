"""what the audit is doing, while it does it

A run that takes two minutes with nothing to show for it reads as a broken page.
The stage and the page count are written as the run moves, so the waiting screen
can say what is happening now.

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-10-01
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("audit_run", sa.Column("stage", sa.String(20), nullable=False, server_default=""))
    op.add_column(
        "audit_run", sa.Column("pages_read", sa.Integer(), nullable=False, server_default="0")
    )


def downgrade() -> None:
    op.drop_column("audit_run", "pages_read")
    op.drop_column("audit_run", "stage")
