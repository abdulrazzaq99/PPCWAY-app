"""Which campaign a change belongs to, so a campaign can show its own history.

The change history tab on a campaign is the fifth of its five tabs, and without
this it would have to be found by matching resource names against everything we
hold in that campaign. A change already knows which campaign it was in when it
is recorded; this is where that is kept.

Revision ID: c5d6e7f8a9b0
Revises: b4c5d6e7f8a9
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "c5d6e7f8a9b0"
down_revision = "b4c5d6e7f8a9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("ads_external_change") as batch:
        batch.add_column(sa.Column("campaign_id", sa.String(20), nullable=False, server_default=""))
    op.create_index("ix_ads_external_change_campaign_id", "ads_external_change", ["campaign_id"])


def downgrade() -> None:
    op.drop_index("ix_ads_external_change_campaign_id", table_name="ads_external_change")
    with op.batch_alter_table("ads_external_change") as batch:
        batch.drop_column("campaign_id")
