"""A campaign starts at a moment, not on a day.

Google Ads API v25 refuses `campaign.start_date` and `campaign.end_date`: since
v23 they are `start_date_time` and `end_date_time`, carrying a time of day in
the account's own zone. The first live sync is what found it. The columns follow
the API rather than paper over it, because the Learning window in week two
counts from exactly this value.

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "f2a3b4c5d6e7"
down_revision = "e1f2a3b4c5d6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("ads_campaign") as batch:
        batch.drop_column("starts_on")
        batch.drop_column("ends_on")
        batch.add_column(sa.Column("starts_at", sa.String(25), nullable=False, server_default=""))
        batch.add_column(sa.Column("ends_at", sa.String(25), nullable=False, server_default=""))


def downgrade() -> None:
    with op.batch_alter_table("ads_campaign") as batch:
        batch.drop_column("starts_at")
        batch.drop_column("ends_at")
        batch.add_column(sa.Column("starts_on", sa.String(10), nullable=False, server_default=""))
        batch.add_column(sa.Column("ends_on", sa.String(10), nullable=False, server_default=""))
