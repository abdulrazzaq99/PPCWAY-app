"""where Google's review of each ad stands

Revision ID: 6c4e1a9b3d27
Revises: 5a2d8f4c7e19
Create Date: 2026-11-11

A new ad's approval is UNKNOWN until Google has reviewed it, and PPCWay read
that as "refused". The review status says whether the review is still in
progress, done, or under appeal, so a refusal is only ever a real one. Filled
by the next structure read.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "6c4e1a9b3d27"
down_revision = "5a2d8f4c7e19"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ads_ad",
        sa.Column("review", sa.String(length=30), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("ads_ad", "review")
