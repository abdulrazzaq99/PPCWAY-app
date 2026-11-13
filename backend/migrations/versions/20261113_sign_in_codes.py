"""six-digit sign-in codes sent by email

Revision ID: 7d3b5e2a9c41
Revises: 6c4e1a9b3d27
Create Date: 2026-11-13

Signing in, or up, with a code emailed to the address instead of a password.
Keyed by the address, because somebody signing up this way has no account
until the code comes back. See `ppcway.auth.codes`.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "7d3b5e2a9c41"
down_revision = "6c4e1a9b3d27"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "account_code",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("code_hash", sa.String(length=255), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_account_code_email", "account_code", ["email"])


def downgrade() -> None:
    op.drop_index("ix_account_code_email", table_name="account_code")
    op.drop_table("account_code")
