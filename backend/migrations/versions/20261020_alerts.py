"""One alert, to one business, about one thing, on one day.

Revision ID: f8a9b0c1d2e3
Revises: e7f8a9b0c1d2
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "f8a9b0c1d2e3"
down_revision = "e7f8a9b0c1d2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mail_alert_sent",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.String(20), nullable=False, server_default=""),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("about", sa.String(100), nullable=False, server_default=""),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("to_address", sa.String(320), nullable=False, server_default=""),
        sa.Column("subject", sa.String(255), nullable=False, server_default=""),
        sa.Column("status", sa.String(10), nullable=False, server_default="sent"),
        sa.Column("trouble", sa.Text(), nullable=False, server_default=""),
        sa.Column("sent_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["account_id"], ["account.id"], name="fk_mail_alert_sent_account_id"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_mail_alert_sent"),
        sa.UniqueConstraint("account_id", "kind", "about", "day", name="one_alert_a_day"),
    )
    op.create_index("ix_mail_alert_sent_account_id", "mail_alert_sent", ["account_id"])
    op.create_index("ix_mail_alert_sent_customer_id", "mail_alert_sent", ["customer_id"])
    op.create_index("ix_mail_alert_sent_kind", "mail_alert_sent", ["kind"])
    op.create_index("ix_mail_alert_sent_day", "mail_alert_sent", ["day"])


def downgrade() -> None:
    op.drop_table("mail_alert_sent")
