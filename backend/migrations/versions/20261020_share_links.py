"""Links that need no login and expire on their own.

Revision ID: d6e7f8a9b0c1
Revises: c5d6e7f8a9b0
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "d6e7f8a9b0c1"
down_revision = "c5d6e7f8a9b0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "share_link",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("subject", sa.String(100), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("made_by", sa.Uuid(), nullable=True),
        sa.Column("sent_to", sa.String(320), nullable=False, server_default=""),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("opened", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organization.id"], name="fk_share_link_organization_id"
        ),
        sa.ForeignKeyConstraint(["made_by"], ["account.id"], name="fk_share_link_made_by"),
        sa.PrimaryKeyConstraint("id", name="pk_share_link"),
        sa.UniqueConstraint("token_hash", name="uq_share_link_token_hash"),
    )
    op.create_index("ix_share_link_kind", "share_link", ["kind"])
    op.create_index("ix_share_link_subject", "share_link", ["subject"])
    op.create_index("ix_share_link_organization_id", "share_link", ["organization_id"])
    op.create_index("ix_share_link_made_by", "share_link", ["made_by"])


def downgrade() -> None:
    op.drop_table("share_link")
