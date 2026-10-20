"""The currency of the account they chose, held with the connection.

Every figure on the dashboard is money, and the dashboard now reads our own
mirror rather than Google. The mirror holds micros, which are currency-free, so
without this column a page served from our database could not say whether a
number was dollars or euros. Google tells us the currency when the account is
chosen; this is where that answer is kept.

Revision ID: a3b4c5d6e7f8
Revises: f2a3b4c5d6e7
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "a3b4c5d6e7f8"
down_revision = "f2a3b4c5d6e7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("ads_connection") as batch:
        batch.add_column(sa.Column("currency", sa.String(3), nullable=False, server_default=""))


def downgrade() -> None:
    with op.batch_alter_table("ads_connection") as batch:
        batch.drop_column("currency")
