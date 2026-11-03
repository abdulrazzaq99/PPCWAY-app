"""the middle band, where a change is too big for the owner and not too big for anybody

Revision ID: c7d8e9f0a1b2
Revises: b6c7d8e9f0a1
Create Date: 2026-11-02

The client settled the 20-versus-25 percent conflict on 30 October, and settled
it in a way that changes the shape of the guardrail rather than one number:
*up to 20% normal route; 20-50% expert route; hard reject over 50% per change
or 100% per day.*

Two numbers become three. `max_change_pct` drops from 25 to 20,
`max_daily_change_pct` rises from 50 to 100, and `expert_max_change_pct`
arrives at 50 to carry the band between them. That middle band is the point:
before it, a merchant who genuinely needed to double a budget got a flat
refusal from a check that could not route them anywhere, which is how a
guardrail ends up switched off rather than respected.

The defaults move for rows created from here on. Existing rows are left alone
deliberately -- `opt_guardrail_config` is immutable by trigger, because an action
cites a version to say which limits authorised it, and rewriting the numbers
inside a version that actions already point at would make every one of those
actions misdescribe itself. A business on the old limits moves by having a new
version written for it, which is the only supported way limits ever change.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "c7d8e9f0a1b2"
down_revision = "b6c7d8e9f0a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # One batch for all three, because SQLite has no ALTER COLUMN SET DEFAULT
    # and batch mode rebuilds the table instead. The test suite runs these
    # migrations against SQLite, so a Postgres-only spelling here is a
    # migration nothing exercises until it reaches production.
    with op.batch_alter_table("opt_guardrail_config") as batch:
        batch.add_column(
            sa.Column(
                "expert_max_change_pct", sa.Float(), nullable=False, server_default="50.0"
            )
        )
        # The column default follows the model's, so a row written by the
        # application and one written by hand in psql agree.
        batch.alter_column("max_change_pct", server_default="20.0", existing_type=sa.Float())
        batch.alter_column(
            "max_daily_change_pct", server_default="100.0", existing_type=sa.Float()
        )


def downgrade() -> None:
    with op.batch_alter_table("opt_guardrail_config") as batch:
        batch.alter_column(
            "max_daily_change_pct", server_default="50.0", existing_type=sa.Float()
        )
        batch.alter_column("max_change_pct", server_default="25.0", existing_type=sa.Float())
        batch.drop_column("expert_max_change_pct")
