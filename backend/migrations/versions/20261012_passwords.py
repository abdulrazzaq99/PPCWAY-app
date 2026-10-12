"""Signing in with an email and a password, and the links that go with it.

Google sign-in was the only way in. A business owner who does not want another
Google account, or whose staff do not have one, could not be invited to use the
product at all.

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "d0e1f2a3b4c5"
down_revision = "c9d0e1f2a3b4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("account") as batch:
        batch.add_column(
            sa.Column("password_hash", sa.String(255), nullable=False, server_default="")
        )
        batch.add_column(sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True))
        # Somebody who signed in with Google has no password and never needs one.
        batch.alter_column("google_sub", existing_type=sa.String(64), nullable=True)

    # Everybody already here arrived through Google, which verifies the address.
    op.execute("UPDATE account SET email_verified_at = created_at WHERE google_sub IS NOT NULL")

    op.create_table(
        "account_link",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("account_id", sa.Uuid(), sa.ForeignKey("account.id"), nullable=False),
        # "verify" or "reset". Spelled out, so a row reads without a lookup.
        sa.Column("purpose", sa.String(20), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_account_link_account_id", "account_link", ["account_id"])
    op.create_index("ix_account_link_token_hash", "account_link", ["token_hash"])


def downgrade() -> None:
    op.drop_table("account_link")
    with op.batch_alter_table("account") as batch:
        batch.alter_column("google_sub", existing_type=sa.String(64), nullable=False)
        batch.drop_column("email_verified_at")
        batch.drop_column("password_hash")
