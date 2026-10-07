"""a merchant's connected Google Ads account

The refresh token is a bearer credential with no expiry, so it is stored
encrypted and nowhere else. The trip to Google is recorded too: the state that
comes back must match one this server started, for an account that is signed in.

Named `ads_connection`, not `google_ads_link`: the proof of concept's schema
shares this database and its `google_ads_link` means a manager-to-client link.

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-10-07
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "f6a7b8c9d0e1"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ads_connection",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "account_id",
            sa.Uuid(),
            sa.ForeignKey("account.id", name="fk_ads_connection_account_id"),
            nullable=False,
        ),
        sa.Column("ciphertext", sa.Text(), nullable=False),
        sa.Column("customer_id", sa.String(20), nullable=False, server_default=""),
        sa.Column("customer_name", sa.String(200), nullable=False, server_default=""),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_ads_connection_account_id", "ads_connection", ["account_id"])

    op.create_table(
        "ads_consent_trip",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("state", sa.String(64), nullable=False),
        sa.Column(
            "account_id",
            sa.Uuid(),
            sa.ForeignKey("account.id", name="fk_ads_consent_trip_account_id"),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_ads_consent_trip_state", "ads_consent_trip", ["state"], unique=True)
    op.create_index("ix_ads_consent_trip_account_id", "ads_consent_trip", ["account_id"])


def downgrade() -> None:
    op.drop_table("ads_consent_trip")
    op.drop_table("ads_connection")
