"""what Google says about the state of the account, so a guardrail can ask

Revision ID: d8e9f0a1b2c3
Revises: c7d8e9f0a1b2
Create Date: 2026-11-02

`account_serviceable`, the second of the ten guardrails, refuses a change to an
account whose state it cannot name. Nothing mirrored that state, so the check
was correct and unanswerable: every approval would have been refused with "we
cannot tell what state this account is in", which is the right refusal for the
wrong reason.

`customer.status` is Google's own word -- ENABLED, SUSPENDED, CANCELED,
CLOSED -- and the structure sync already reads the customer resource, so this
costs no extra request.

Empty is kept as a state, and it is not "healthy". An account nobody has read
yet fails the check, which is what should happen: the alternative is a default
that says "fine" about an account we have never looked at.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "d8e9f0a1b2c3"
down_revision = "c7d8e9f0a1b2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("ads_connection") as batch:
        batch.add_column(
            sa.Column("account_status", sa.String(length=20), nullable=False, server_default="")
        )
        batch.add_column(
            sa.Column("status_read_at", sa.DateTime(timezone=True), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("ads_connection") as batch:
        batch.drop_column("status_read_at")
        batch.drop_column("account_status")
