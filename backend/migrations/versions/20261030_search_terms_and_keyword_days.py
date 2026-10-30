"""what people actually typed, what each keyword did, and how much of the auction we saw

Revision ID: a5b6c7d8e9f0
Revises: f4a5b6c7d8e9
Create Date: 2026-10-30

Phase 0.3 of the client's brief: the three mirrors the recommendation engine
cannot be written without. Phase 1's rules read these and nothing else, so they
come first.

**Why impression share is four columns on `ads_campaign_day` and not a third
table.** The grain is identical -- one campaign, one day -- and that table
already exists with a unique constraint saying so. A separate table would add a
join to every screen that reads this one, and a second refresh path that could
disagree with the first about the same afternoon. Nullable rather than defaulted
to zero: a campaign that is not a Search campaign has no search impression
share, and zero would read as "you appeared in none of the auctions", which is
a different and far more alarming claim than "Google did not say".

**Why search terms are keyed by a hash.** A search term is what a person typed
and runs to sentences; Google does not truncate them, so neither do we, and a
1000-character column cannot carry an index or a unique constraint. `term_hash`
is the term case-folded, space-collapsed and hashed, which is also what stops
"boiler  repair" and "boiler repair" becoming two rows that each sit just under
a rule's spend threshold.

**Why both are per day rather than per window.** A rule asking for thirty days
and a rule asking for seven must not need two tables, and the freshness
guardrail needs to know when a figure was true rather than only what it was.
This is the same decision `ads_campaign_day` already made, for the same reason.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "a5b6c7d8e9f0"
down_revision = "f4a5b6c7d8e9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("ads_campaign_day") as batch:
        batch.add_column(sa.Column("search_share", sa.Float(), nullable=True))
        batch.add_column(sa.Column("lost_to_budget", sa.Float(), nullable=True))
        batch.add_column(sa.Column("lost_to_rank", sa.Float(), nullable=True))
        batch.add_column(sa.Column("top_share", sa.Float(), nullable=True))

    op.create_table(
        "ads_search_term_day",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("customer_id", sa.String(length=20), nullable=False),
        sa.Column("campaign_id", sa.String(length=20), nullable=False, server_default=""),
        sa.Column("ad_group_id", sa.String(length=20), nullable=False, server_default=""),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("term", sa.String(length=1000), nullable=False),
        sa.Column("term_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default=""),
        sa.Column("matched_keyword", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("impressions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("clicks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_micros", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("conversions", sa.Float(), nullable=False, server_default="0"),
        sa.Column("conversion_value_micros", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "refreshed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "customer_id", "ad_group_id", "term_hash", "day", name="one_term_a_day"
        ),
    )
    op.create_index("ix_ads_search_term_day_customer_id", "ads_search_term_day", ["customer_id"])
    op.create_index("ix_ads_search_term_day_campaign_id", "ads_search_term_day", ["campaign_id"])
    op.create_index("ix_ads_search_term_day_ad_group_id", "ads_search_term_day", ["ad_group_id"])
    op.create_index("ix_ads_search_term_day_day", "ads_search_term_day", ["day"])
    op.create_index("ix_ads_search_term_day_term_hash", "ads_search_term_day", ["term_hash"])

    op.create_table(
        "ads_keyword_day",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("customer_id", sa.String(length=20), nullable=False),
        sa.Column("criterion_id", sa.String(length=20), nullable=False),
        sa.Column("ad_group_id", sa.String(length=20), nullable=False, server_default=""),
        sa.Column("campaign_id", sa.String(length=20), nullable=False, server_default=""),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("text", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("match_type", sa.String(length=20), nullable=False, server_default=""),
        sa.Column("impressions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("clicks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_micros", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("conversions", sa.Float(), nullable=False, server_default="0"),
        sa.Column("conversion_value_micros", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "refreshed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("customer_id", "criterion_id", "day", name="one_keyword_a_day"),
    )
    op.create_index("ix_ads_keyword_day_customer_id", "ads_keyword_day", ["customer_id"])
    op.create_index("ix_ads_keyword_day_criterion_id", "ads_keyword_day", ["criterion_id"])
    op.create_index("ix_ads_keyword_day_ad_group_id", "ads_keyword_day", ["ad_group_id"])
    op.create_index("ix_ads_keyword_day_campaign_id", "ads_keyword_day", ["campaign_id"])
    op.create_index("ix_ads_keyword_day_day", "ads_keyword_day", ["day"])

    # Both join their tenant through `ads_connection.customer_id`, exactly as
    # the other mirror tables do -- see 20261030_tenant_isolation.py for why a
    # subquery was chosen over a denormalised organisation column.
    if op.get_bind().dialect.name != "postgresql":
        return
    for table in ("ads_search_term_day", "ads_keyword_day"):
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO ppcway_app")
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY {table}_tenant_isolation ON {table}
            USING (customer_id IN (SELECT customer_id FROM ads_connection
                   WHERE organization_id =
                     NULLIF(current_setting('app.current_org_id', true), '')::uuid
                     AND customer_id <> ''))
            WITH CHECK (customer_id IN (SELECT customer_id FROM ads_connection
                   WHERE organization_id =
                     NULLIF(current_setting('app.current_org_id', true), '')::uuid
                     AND customer_id <> ''))
            """
        )


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        for table in ("ads_search_term_day", "ads_keyword_day"):
            op.execute(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table}")
    op.drop_table("ads_keyword_day")
    op.drop_table("ads_search_term_day")
    with op.batch_alter_table("ads_campaign_day") as batch:
        batch.drop_column("top_share")
        batch.drop_column("lost_to_rank")
        batch.drop_column("lost_to_budget")
        batch.drop_column("search_share")
