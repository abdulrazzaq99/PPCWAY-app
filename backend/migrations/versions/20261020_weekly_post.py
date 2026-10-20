"""One row a week per account, so the Monday summary is sent once.

Revision ID: b4c5d6e7f8a9
Revises: a3b4c5d6e7f8
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "b4c5d6e7f8a9"
down_revision = "a3b4c5d6e7f8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mail_weekly_post",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.String(20), nullable=False, server_default=""),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("to_address", sa.String(320), nullable=False, server_default=""),
        sa.Column("status", sa.String(10), nullable=False, server_default="sent"),
        sa.Column("trouble", sa.Text(), nullable=False, server_default=""),
        sa.Column("subject", sa.String(255), nullable=False, server_default=""),
        sa.Column("sent_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["account_id"], ["account.id"], name="fk_mail_weekly_post_account_id"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_mail_weekly_post"),
        sa.UniqueConstraint("account_id", "week_start", name="one_post_a_week"),
    )
    op.create_index("ix_mail_weekly_post_account_id", "mail_weekly_post", ["account_id"])
    op.create_index("ix_mail_weekly_post_customer_id", "mail_weekly_post", ["customer_id"])
    op.create_index("ix_mail_weekly_post_week_start", "mail_weekly_post", ["week_start"])


def downgrade() -> None:
    op.drop_table("mail_weekly_post")
