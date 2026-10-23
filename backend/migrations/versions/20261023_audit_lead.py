"""The audit's visitor becomes a lead, and proves their address with a code.

Revision ID: a9b0c1d2e3f4
Revises: f8a9b0c1d2e3
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "a9b0c1d2e3f4"
down_revision = "f8a9b0c1d2e3"
branch_labels = None
depends_on = None

#: Everything added to the request, which is where the lead already lived.
COLUMNS = [
    sa.Column("runner", sa.String(20), nullable=False, server_default=""),
    sa.Column("goal", sa.String(20), nullable=False, server_default=""),
    sa.Column("spend_band", sa.String(20), nullable=False, server_default=""),
    sa.Column("came_from", sa.JSON(), nullable=True),
    sa.Column("tips_opt_in", sa.Boolean(), nullable=False, server_default=sa.false()),
    sa.Column("tips_opt_in_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
]


def upgrade() -> None:
    with op.batch_alter_table("audit_request") as batch:
        for column in COLUMNS:
            batch.add_column(column)
    op.create_index("ix_audit_request_verified_at", "audit_request", ["verified_at"])

    op.create_table(
        "audit_email_code",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("code_hash", sa.String(64), nullable=False),
        sa.Column("sent_to", sa.String(320), nullable=False, server_default=""),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sent_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["request_id"], ["audit_request.id"], name="fk_audit_email_code_request_id"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_audit_email_code"),
    )
    op.create_index("ix_audit_email_code_request_id", "audit_email_code", ["request_id"])
    op.create_index("ix_audit_email_code_code_hash", "audit_email_code", ["code_hash"])


def downgrade() -> None:
    op.drop_table("audit_email_code")
    op.drop_index("ix_audit_request_verified_at", table_name="audit_request")
    with op.batch_alter_table("audit_request") as batch:
        for column in COLUMNS:
            batch.drop_column(column.name)
