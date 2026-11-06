"""a new campaign being built, and the record of its launch

Revision ID: 8d3f1a6c2e94
Revises: 6b2e9d4a1c57
Create Date: 2026-11-06

The campaign builder's workspace: the plan between "start writing" and
"launch", and afterwards what Google created and who launched it. Scoped to
the business like every other table that carries `organization_id`.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "8d3f1a6c2e94"
down_revision = "6b2e9d4a1c57"
branch_labels = None
depends_on = None

_MINE = "organization_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid"


def upgrade() -> None:
    op.create_table(
        "campaign_draft",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organization.id"), nullable=False),
        sa.Column("customer_id", sa.String(length=20), nullable=False, server_default=""),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("account.id"), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("plan", sa.JSON(), nullable=True),
        sa.Column("launched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("launched_by", sa.Uuid(), nullable=True),
        sa.Column("campaign_resource", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("outcome", sa.JSON(), nullable=True),
    )
    op.create_index("ix_campaign_draft_organization_id", "campaign_draft", ["organization_id"])
    op.create_index("ix_campaign_draft_customer_id", "campaign_draft", ["customer_id"])
    op.create_index("ix_campaign_draft_created_at", "campaign_draft", ["created_at"])
    op.create_index("ix_campaign_draft_status", "campaign_draft", ["status"])

    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON campaign_draft TO ppcway_app")
    op.execute("ALTER TABLE campaign_draft ENABLE ROW LEVEL SECURITY")
    op.execute(
        f"""
        CREATE POLICY campaign_draft_tenant_isolation ON campaign_draft
        USING ({_MINE}) WITH CHECK ({_MINE})
        """
    )


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP POLICY IF EXISTS campaign_draft_tenant_isolation ON campaign_draft")
    op.drop_index("ix_campaign_draft_status", table_name="campaign_draft")
    op.drop_index("ix_campaign_draft_created_at", table_name="campaign_draft")
    op.drop_index("ix_campaign_draft_customer_id", table_name="campaign_draft")
    op.drop_index("ix_campaign_draft_organization_id", table_name="campaign_draft")
    op.drop_table("campaign_draft")
