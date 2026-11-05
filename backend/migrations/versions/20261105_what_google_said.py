"""what Google said about a change, and which sender took it to make it

Revision ID: 9e1f5a7c3b20
Revises: b4f81c6d2e07
Create Date: 2026-11-05

The write path, step 3 of the owner's list: an approved change now reaches
Google. Two facts about that attempt had nowhere to live.

`outcome` is what happened at the door: what each operation created, what
Google refused and in what words, or the ruling that stopped the change before
it was sent. Undoing an exclusion needs it -- only Google knows the id of the
negative keyword it created, and the undo is a remove of exactly that -- and a
merchant whose change failed is owed the reason rather than a bare status.

`taken_at` is when one sender took the change to make it. It is set by an
update that only one sender can win, which is what makes a change go to Google
at most once however many senders reach it: the request that approved it, the
scheduled pass, and a retry of either.

Both are write-once, guarded the way `rechecked` is: a trigger function of its
own, added beside the existing ones, so the transition list and every other
tier stay exactly as the previous revisions left them. A sender that could
clear `taken_at` could send twice, and an outcome that could be rewritten would
let the log say a change landed when Google said it did not.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "9e1f5a7c3b20"
down_revision = "b4f81c6d2e07"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("opt_action") as batch:
        batch.add_column(sa.Column("taken_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("outcome", sa.JSON(), nullable=True))

    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute(
        """
        CREATE OR REPLACE FUNCTION opt_action_outcome_once() RETURNS trigger AS $fn$
        BEGIN
          IF OLD.taken_at IS NOT NULL
             AND NEW.taken_at IS DISTINCT FROM OLD.taken_at THEN
            RAISE EXCEPTION
              'opt_action.taken_at was already written and may not change';
          END IF;
          IF OLD.outcome IS NOT NULL
             AND NEW.outcome::text IS DISTINCT FROM OLD.outcome::text THEN
            RAISE EXCEPTION
              'opt_action.outcome was already written and may not change';
          END IF;
          RETURN NEW;
        END;
        $fn$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER opt_action_outcome_once_trg
          BEFORE UPDATE ON opt_action
          FOR EACH ROW EXECUTE FUNCTION opt_action_outcome_once()
        """
    )


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS opt_action_outcome_once_trg ON opt_action")
        op.execute("DROP FUNCTION IF EXISTS opt_action_outcome_once()")
    with op.batch_alter_table("opt_action") as batch:
        batch.drop_column("outcome")
        batch.drop_column("taken_at")
