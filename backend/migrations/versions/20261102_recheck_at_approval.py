"""the second ruling, because the first one was made at a different time

Revision ID: e9f0a1b2c3d4
Revises: d8e9f0a1b2c3
Create Date: 2026-11-02

The client's brief requires the guardrails to be re-run at approval, and that
produces a second decision about the same row -- made days later, against
figures that may have gone stale, a day's budget that may have moved, an
account that may have been suspended since.

`decided_by` and `decided_because` cannot carry it. They are write-once,
deliberately: they record the decision that produced the row's first status,
and a log whose reasons can be rewritten is not a log. So the second ruling
gets its own pair of columns, and an action refused at approval can say which
of the two refusals it was and when -- which is the question a merchant asks
when something they said yes to did not happen.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "e9f0a1b2c3d4"
down_revision = "d8e9f0a1b2c3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("optimization_action") as batch:
        batch.add_column(sa.Column("rechecked", sa.JSON(), nullable=True))
        batch.add_column(sa.Column("rechecked_at", sa.DateTime(timezone=True), nullable=True))

    if op.get_bind().dialect.name != "postgresql":
        return
    # Write-once, like every other column the log fills in later: the second
    # ruling may be recorded once and never revised. The guard is added to the
    # existing function rather than the function being rewritten, so the
    # transition list and every other tier stay exactly as the previous
    # revision left them.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION optimization_action_recheck_once() RETURNS trigger AS $fn$
        BEGIN
          IF OLD.rechecked IS NOT NULL
             AND NEW.rechecked::text IS DISTINCT FROM OLD.rechecked::text THEN
            RAISE EXCEPTION
              'optimization_action.rechecked was already written and may not change';
          END IF;
          IF OLD.rechecked_at IS NOT NULL
             AND NEW.rechecked_at IS DISTINCT FROM OLD.rechecked_at THEN
            RAISE EXCEPTION
              'optimization_action.rechecked_at was already written and may not change';
          END IF;
          RETURN NEW;
        END;
        $fn$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER optimization_action_recheck_once_trg
          BEFORE UPDATE ON optimization_action
          FOR EACH ROW EXECUTE FUNCTION optimization_action_recheck_once()
        """
    )


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            "DROP TRIGGER IF EXISTS optimization_action_recheck_once_trg ON optimization_action"
        )
        op.execute("DROP FUNCTION IF EXISTS optimization_action_recheck_once()")
    with op.batch_alter_table("optimization_action") as batch:
        batch.drop_column("rechecked_at")
        batch.drop_column("rechecked")
