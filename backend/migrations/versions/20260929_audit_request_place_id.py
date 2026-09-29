"""the Google listing a person picked in Find my business

Only the place id is kept: Google's terms allow storing that and nothing else from
a listing, so the name, rating and hours are read again each time a screen shows them.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-09-29
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "audit_request",
        sa.Column("place_id", sa.String(200), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("audit_request", "place_id")
