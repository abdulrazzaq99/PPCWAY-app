"""each campaign's budget, by name, and whether it is shared

Revision ID: 5a2d8f4c7e19
Revises: 3e7c5a9b1d48
Create Date: 2026-11-10

Otto's budget suggestions send a change to the budget itself, so the mirror
keeps its resource name, and whether other campaigns share it: a shared budget
is never changed for one campaign's sake. Filled by the next structure read.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "5a2d8f4c7e19"
down_revision = "3e7c5a9b1d48"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ads_campaign",
        sa.Column("budget_resource", sa.String(length=255), nullable=False, server_default=""),
    )
    op.add_column(
        "ads_campaign",
        sa.Column("budget_shared", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("ads_campaign", "budget_shared")
    op.drop_column("ads_campaign", "budget_resource")
