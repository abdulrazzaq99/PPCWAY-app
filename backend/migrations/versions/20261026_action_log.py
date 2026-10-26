"""The optimization action log, and the versioned limits that authorised each row.

Revision ID: c1d2e3f4a5b6
Revises: b0c1d2e3f4a5
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "c1d2e3f4a5b6"
down_revision = "b0c1d2e3f4a5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "guardrail_config",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("autonomy", sa.String(20), nullable=False, server_default="approve_first"),
        sa.Column("max_daily_budget", sa.Float(), nullable=False, server_default="0"),
        sa.Column("max_cpa", sa.Float(), nullable=False, server_default="0"),
        sa.Column("min_bid", sa.Float(), nullable=False, server_default="0"),
        sa.Column("max_bid", sa.Float(), nullable=False, server_default="0"),
        sa.Column("max_change_pct", sa.Float(), nullable=False, server_default="25"),
        sa.Column("max_daily_change_pct", sa.Float(), nullable=False, server_default="50"),
        sa.Column("max_changes_per_entity_day", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("max_changes_per_day", sa.Integer(), nullable=False, server_default="20"),
        sa.Column("max_pause_pct", sa.Float(), nullable=False, server_default="10"),
        sa.Column("staleness_minutes", sa.Integer(), nullable=False, server_default="180"),
        sa.Column("hands_off", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organization.id"], name="fk_guardrail_config_organization_id"
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["account.id"], name="fk_guardrail_config_created_by"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_guardrail_config"),
        sa.UniqueConstraint("organization_id", "version", name="one_version_once"),
    )
    op.create_index("ix_guardrail_config_organization_id", "guardrail_config", ["organization_id"])
    op.create_index("ix_guardrail_config_version", "guardrail_config", ["version"])

    op.create_table(
        "optimization_action",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.String(20), nullable=False, server_default=""),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("target_kind", sa.String(20), nullable=False, server_default=""),
        sa.Column("target_id", sa.String(64), nullable=False, server_default=""),
        sa.Column("target_label", sa.String(255), nullable=False, server_default=""),
        sa.Column("before", sa.JSON(), nullable=True),
        sa.Column("after", sa.JSON(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("evidence", sa.JSON(), nullable=True),
        sa.Column("rule_id", sa.String(60), nullable=False, server_default=""),
        sa.Column("rule_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("guardrail_config_version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("autonomy", sa.String(20), nullable=False, server_default=""),
        sa.Column("job_run", sa.String(64), nullable=False, server_default=""),
        sa.Column("route", sa.String(20), nullable=False, server_default="owner"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("decided_by", sa.String(40), nullable=False, server_default=""),
        sa.Column("decided_because", sa.Text(), nullable=False, server_default=""),
        sa.Column("idempotency_key", sa.String(80), nullable=False, server_default=""),
        sa.Column("undo_of", sa.Uuid(), nullable=True),
        sa.Column("reversible", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("approved_by", sa.Uuid(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organization.id"], name="fk_optimization_action_organization_id"
        ),
        sa.ForeignKeyConstraint(
            ["undo_of"], ["optimization_action.id"], name="fk_optimization_action_undo_of"
        ),
        sa.ForeignKeyConstraint(
            ["approved_by"], ["account.id"], name="fk_optimization_action_approved_by"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_optimization_action"),
    )
    for column in (
        "organization_id",
        "customer_id",
        "kind",
        "target_id",
        "job_run",
        "status",
        "idempotency_key",
        "undo_of",
        "created_at",
    ):
        op.create_index(f"ix_optimization_action_{column}", "optimization_action", [column])


def downgrade() -> None:
    op.drop_table("optimization_action")
    op.drop_table("guardrail_config")
