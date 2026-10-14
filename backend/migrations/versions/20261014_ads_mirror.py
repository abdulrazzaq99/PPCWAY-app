"""The account as we last saw it: campaigns, ad groups, keywords, ads and days.

Every screen reads Google live today. These tables are what they will read
instead, and what the recommendation engine reads after that. Nothing is
dropped: the live reads keep working until the screens are moved over.

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "e1f2a3b4c5d6"
down_revision = "d0e1f2a3b4c5"
branch_labels = None
depends_on = None


#: What every mirrored thing carries. Repeated per table rather than factored
#: into a loop, so a migration reads as the tables it makes.
def _mirrored() -> list[sa.Column]:  # type: ignore[type-arg]
    return [
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("customer_id", sa.String(20), nullable=False, index=True),
        sa.Column("resource_name", sa.String(255), nullable=False, unique=True, index=True),
        sa.Column("fingerprint", sa.String(64), nullable=False, server_default=""),
        sa.Column("source", sa.String(10), nullable=False, server_default="google"),
        sa.Column("seen_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("gone_at", sa.DateTime(timezone=True), nullable=True),
    ]


def upgrade() -> None:
    op.create_table(
        "ads_campaign",
        *_mirrored(),
        sa.Column("campaign_id", sa.String(20), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False, server_default=""),
        sa.Column("status", sa.String(20), nullable=False, server_default=""),
        sa.Column("channel", sa.String(30), nullable=False, server_default=""),
        sa.Column("bidding", sa.String(40), nullable=False, server_default=""),
        sa.Column("budget_micros", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("starts_on", sa.String(10), nullable=False, server_default=""),
        sa.Column("ends_on", sa.String(10), nullable=False, server_default=""),
    )
    op.create_table(
        "ads_ad_group",
        *_mirrored(),
        sa.Column("ad_group_id", sa.String(20), nullable=False, index=True),
        sa.Column("campaign_id", sa.String(20), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False, server_default=""),
        sa.Column("status", sa.String(20), nullable=False, server_default=""),
        sa.Column("cpc_bid_micros", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_table(
        "ads_keyword",
        *_mirrored(),
        sa.Column("criterion_id", sa.String(20), nullable=False, index=True),
        sa.Column("ad_group_id", sa.String(20), nullable=False, index=True),
        sa.Column("campaign_id", sa.String(20), nullable=False, index=True),
        sa.Column("text", sa.String(255), nullable=False, server_default=""),
        sa.Column("match_type", sa.String(20), nullable=False, server_default=""),
        sa.Column("status", sa.String(20), nullable=False, server_default=""),
        sa.Column("negative", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("quality_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cpc_bid_micros", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_table(
        "ads_ad",
        *_mirrored(),
        sa.Column("ad_id", sa.String(20), nullable=False, index=True),
        sa.Column("ad_group_id", sa.String(20), nullable=False, index=True),
        sa.Column("campaign_id", sa.String(20), nullable=False, index=True),
        sa.Column("kind", sa.String(40), nullable=False, server_default=""),
        sa.Column("status", sa.String(20), nullable=False, server_default=""),
        sa.Column("approval", sa.String(30), nullable=False, server_default=""),
        sa.Column("headlines", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("descriptions", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("final_urls", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.create_table(
        "ads_campaign_day",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("customer_id", sa.String(20), nullable=False, index=True),
        sa.Column("campaign_id", sa.String(20), nullable=False, index=True),
        sa.Column("day", sa.Date(), nullable=False, index=True),
        sa.Column("impressions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("clicks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_micros", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("conversions", sa.Float(), nullable=False, server_default="0"),
        sa.Column("conversion_value_micros", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("calls", sa.Float(), nullable=False, server_default="0"),
        sa.Column("forms", sa.Float(), nullable=False, server_default="0"),
        sa.Column("refreshed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("customer_id", "campaign_id", "day", name="one_row_a_day"),
    )
    op.create_table(
        "ads_sync_run",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("customer_id", sa.String(20), nullable=False, index=True),
        sa.Column("kind", sa.String(20), nullable=False, server_default="structure"),
        sa.Column("status", sa.String(10), nullable=False, server_default="running", index=True),
        sa.Column("stage", sa.String(60), nullable=False, server_default=""),
        sa.Column("counts", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("trouble", sa.Text(), nullable=False, server_default=""),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "ads_external_change",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("customer_id", sa.String(20), nullable=False, index=True),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("resource_name", sa.String(255), nullable=False, index=True),
        sa.Column("label", sa.String(255), nullable=False, server_default=""),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("before", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("after", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("noticed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    for table in (
        "ads_external_change",
        "ads_sync_run",
        "ads_campaign_day",
        "ads_ad",
        "ads_keyword",
        "ads_ad_group",
        "ads_campaign",
    ):
        op.drop_table(table)
