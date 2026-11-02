"""the switch that stops writes, and the tally that says how much is left

Revision ID: f0a1b2c3d4e5
Revises: e9f0a1b2c3d4
Create Date: 2026-11-02

Phase 2.3's two tables.

`ads_kill_switch` is a row rather than a setting, because stopping writes has
to need no deploy. The morning a rule turns out to be wrong across three
hundred accounts, a deploy takes minutes and a row takes seconds. It is
append-shaped too: who stopped it, when and why are the answer to "why did
nothing happen last Tuesday", and a boolean somebody flipped back answers none
of it.

`ads_quota_day` counts operations rather than requests, because Google does.
One mutate carrying four hundred keywords spends four hundred, and a platform
counting requests would believe it had used three of fifteen thousand on the
morning it used twelve hundred.

Both are covered by row-level security through `ads_connection`, like the rest
of the per-account tables -- except the global kill switch, whose `customer_id`
is empty and which therefore belongs to no tenant. That row is PPCWay's, not a
merchant's, and the policy lets it through so that a scoped read can still see
that writes are stopped for everybody.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "f0a1b2c3d4e5"
down_revision = "e9f0a1b2c3d4"
branch_labels = None
depends_on = None

_MINE = """
customer_id = '' OR customer_id IN (
  SELECT customer_id FROM ads_connection
  WHERE organization_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid
    AND customer_id <> ''
)
"""


def upgrade() -> None:
    op.create_table(
        "ads_kill_switch",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("customer_id", sa.String(length=20), nullable=False, server_default=""),
        sa.Column("because", sa.Text(), nullable=False, server_default=""),
        sa.Column("pulled_by", sa.Uuid(), nullable=True),
        sa.Column(
            "pulled_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("released_by", sa.Uuid(), nullable=True),
        sa.Column("ours", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.create_index("ix_ads_kill_switch_customer_id", "ads_kill_switch", ["customer_id"])
    op.create_index("ix_ads_kill_switch_pulled_at", "ads_kill_switch", ["pulled_at"])

    op.create_table(
        "ads_quota_day",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("customer_id", sa.String(length=20), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("warned", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("customer_id", "day", name="one_tally_a_day"),
    )
    op.create_index("ix_ads_quota_day_customer_id", "ads_quota_day", ["customer_id"])
    op.create_index("ix_ads_quota_day_day", "ads_quota_day", ["day"])

    if op.get_bind().dialect.name != "postgresql":
        return
    for table in ("ads_kill_switch", "ads_quota_day"):
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO ppcway_app")
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY {table}_tenant_isolation ON {table}
            USING ({_MINE}) WITH CHECK ({_MINE})
            """
        )


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        for table in ("ads_kill_switch", "ads_quota_day"):
            op.execute(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table}")
    op.drop_table("ads_quota_day")
    op.drop_table("ads_kill_switch")
