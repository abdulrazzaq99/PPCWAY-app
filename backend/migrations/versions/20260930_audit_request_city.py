"""the town they typed, kept for the nearby comparison

Google publishes no coordinates for a business that serves an area rather than
holding a shopfront, which is most trades. Without the town there is nothing to
anchor "the same trade nearby" on, and an unanchored search lands wherever the
server happens to be.

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-09-30
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "audit_request",
        sa.Column("city", sa.String(120), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("audit_request", "city")
