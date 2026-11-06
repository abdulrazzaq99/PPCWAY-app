"""each Google Ads account's own time zone, so its days are its days

Revision ID: 6b2e9d4a1c57
Revises: 4c8d2b6e9f13
Create Date: 2026-11-06

Google files an account's figures under dates in the account's time zone, and
its "last 30 days" ends at the account's yesterday. Every window here ended at
the UTC yesterday, so the screens turned the day over at an hour that meant
nothing to the merchant, and the hourly read asked for a day that had not
started in the account yet. See `ppcway.ads.clock`.

Empty until read. The account picker reads it when the account is chosen, and
every structure read fills it in, so existing connections have it within a
quarter of an hour of this shipping. Until then they are dated in UTC as before.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "6b2e9d4a1c57"
down_revision = "4c8d2b6e9f13"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("ads_connection") as batch:
        batch.add_column(
            sa.Column("time_zone", sa.String(length=40), nullable=False, server_default="")
        )


def downgrade() -> None:
    with op.batch_alter_table("ads_connection") as batch:
        batch.drop_column("time_zone")
