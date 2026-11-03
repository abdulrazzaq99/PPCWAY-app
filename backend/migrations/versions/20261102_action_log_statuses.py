"""the eight states a proposed change can be in, and when it stops being on offer

Revision ID: b6c7d8e9f0a1
Revises: a5b6c7d8e9f0
Create Date: 2026-11-02

Phase 2.1 of the client's brief, which specifies this table in full: the eight
statuses, the expiry date, the "proposed by" column, and the fields a card was
always showing but the log was not keeping -- what we expected the change to be
worth, the undo plan in the words the merchant was shown, and the window the
figures covered.

**Why eight states rather than four.** Each of the four new ones answers a
question the old set made unanswerable:

  * `proposed` and `awaiting_approval` are different: one is waiting on a
    guardrail, the other on a person. A merchant asking why nothing has
    happened is owed the difference.
  * `expired` is not `rejected`. Nobody said no; the offer went stale. A report
    that counted them together would make a merchant look as though they had
    refused things they never saw.
  * `reverted` is the state the undo story rests on, and the brief is explicit
    that a revert is a new row -- so this is the state of the row that *was*
    reverted, not of the revert itself.
  * `failed` is Google refusing, which is nobody's decision at all and must not
    be filed next to a rejection.

**The append-only trigger is replaced, not amended.** `20261030_append_only_log`
enumerated the transitions its four statuses allowed, and said in its own notes
that adding statuses would mean a new `CREATE OR REPLACE FUNCTION`. This is it.
The list below is written out rather than imported from `ppcway.opt.models`,
because a migration is a historical record: one that read the current model
would change what it did to a database as the code moved on, which is the one
thing a migration may never do. `tests/opt/test_append_only_db.py` compares the
live trigger against `MOVES` instead, so the two cannot drift in silence.

**`expires_at` is immutable, not write-once.** Nothing may extend a deadline
after the fact. A proposal that ran out of time and then acquired another week
would make the expiry meaningless and the log untrustworthy about exactly the
thing it is for.

The status rename is defensive rather than needed: nothing writes to this table
in production yet, but a row left on the old `pending` spelling would be
invisible to every query and to the trigger's transition list.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

_TRIGGER = """
CREATE TRIGGER opt_action_append_only_trg
  BEFORE UPDATE OR DELETE ON opt_action
  FOR EACH ROW EXECUTE FUNCTION opt_action_append_only()
"""

revision = "b6c7d8e9f0a1"
down_revision = "a5b6c7d8e9f0"
branch_labels = None
depends_on = None


#: Set when the row is written, never different afterwards.
IMMUTABLE = (
    "id",
    "organization_id",
    "customer_id",
    "kind",
    "target_kind",
    "target_id",
    "target_label",
    "rule_id",
    "rule_version",
    "guardrail_config_version",
    "autonomy",
    "job_run",
    "route",
    "risk",
    "proposed_by",
    "idempotency_key",
    "undo_of",
    "reversible",
    "undo_plan",
    "window_start",
    "window_end",
    "created_at",
    "expires_at",
)
IMMUTABLE_JSON = ("before", "after", "payload", "evidence", "expected_impact")

#: Filled in once, during the one transition that sets each, then frozen.
WRITE_ONCE_TEXT = ("reason", "decided_by", "decided_because")
WRITE_ONCE_VALUE = ("approved_by", "approved_at", "applied_at", "reverted_at")

#: Every move a row may make. Mirrors `ppcway.opt.models.MOVES`; a test
#: compares the two rather than trusting this comment.
TRANSITIONS = (
    "proposed>awaiting_approval",
    "proposed>approved",
    "proposed>rejected",
    "proposed>expired",
    "awaiting_approval>approved",
    "awaiting_approval>rejected",
    "awaiting_approval>expired",
    "approved>applied",
    "approved>failed",
    "approved>rejected",
    "applied>reverted",
)


def _append_only_sql(
    *,
    immutable: tuple[str, ...],
    immutable_json: tuple[str, ...],
    write_once_text: tuple[str, ...],
    write_once_value: tuple[str, ...],
    transitions: tuple[str, ...],
) -> str:
    """Build the function body, one guard per column so a refusal names it.

    The tiers are arguments rather than read from the module, because the
    downgrade has to build the previous revision's version of this function
    against the columns that will still exist once it has dropped the new ones.
    """
    guards = []
    for column in immutable:
        guards.append(
            f"  IF NEW.{column} IS DISTINCT FROM OLD.{column} THEN\n"
            f"    RAISE EXCEPTION 'opt_action.{column} is evidence and may not change';\n"
            f"  END IF;"
        )
    for column in immutable_json:
        guards.append(
            f"  IF NEW.{column}::text IS DISTINCT FROM OLD.{column}::text THEN\n"
            f"    RAISE EXCEPTION 'opt_action.{column} is evidence and may not change';\n"
            f"  END IF;"
        )
    for column in write_once_text:
        guards.append(
            f"  IF COALESCE(OLD.{column}, '') <> ''"
            f" AND NEW.{column} IS DISTINCT FROM OLD.{column} THEN\n"
            f"    RAISE EXCEPTION"
            f" 'opt_action.{column} was already written and may not change';\n"
            f"  END IF;"
        )
    for column in write_once_value:
        guards.append(
            f"  IF OLD.{column} IS NOT NULL"
            f" AND NEW.{column} IS DISTINCT FROM OLD.{column} THEN\n"
            f"    RAISE EXCEPTION"
            f" 'opt_action.{column} was already written and may not change';\n"
            f"  END IF;"
        )
    checks = "\n\n".join(guards)
    allowed = ",".join(f"'{t}'" for t in transitions)
    return f"""
CREATE OR REPLACE FUNCTION opt_action_append_only() RETURNS trigger AS $fn$
DECLARE
  allowed text[] := ARRAY[{allowed}];
BEGIN
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION 'opt_action is append-only: DELETE is forbidden';
  END IF;

  IF NEW.status IS DISTINCT FROM OLD.status
     AND NOT ((OLD.status || '>' || NEW.status) = ANY(allowed)) THEN
    RAISE EXCEPTION
      'opt_action: % -> % is not an allowed transition', OLD.status, NEW.status;
  END IF;

{checks}

  RETURN NEW;
END;
$fn$ LANGUAGE plpgsql;
"""


def upgrade() -> None:
    with op.batch_alter_table("opt_action") as batch:
        batch.add_column(
            sa.Column("risk", sa.String(length=10), nullable=False, server_default="medium")
        )
        batch.add_column(
            sa.Column("proposed_by", sa.String(length=10), nullable=False, server_default="rule")
        )
        batch.add_column(sa.Column("expected_impact", sa.JSON(), nullable=True))
        batch.add_column(sa.Column("undo_plan", sa.Text(), nullable=False, server_default=""))
        batch.add_column(sa.Column("window_start", sa.Date(), nullable=True))
        batch.add_column(sa.Column("window_end", sa.Date(), nullable=True))
        batch.add_column(sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("reverted_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_opt_action_risk", "opt_action", ["risk"])
    op.create_index("ix_opt_action_proposed_by", "opt_action", ["proposed_by"])
    op.create_index("ix_opt_action_expires_at", "opt_action", ["expires_at"])

    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    # The trigger forbids every UPDATE it does not recognise, including this
    # one, so it goes before the rename rather than after it.
    op.execute("DROP TRIGGER IF EXISTS opt_action_append_only_trg ON opt_action")
    op.execute("UPDATE opt_action SET status = 'proposed' WHERE status = 'pending'")
    op.execute(
        sa.text(
            _append_only_sql(
                immutable=IMMUTABLE,
                immutable_json=IMMUTABLE_JSON,
                write_once_text=WRITE_ONCE_TEXT,
                write_once_value=WRITE_ONCE_VALUE,
                transitions=TRANSITIONS,
            )
        )
    )
    op.execute(_TRIGGER)


#: The transitions the previous revision allowed. Here so that a downgrade
#: puts the log back the way it found it rather than leaving it editable: a
#: database sitting between these two revisions with no trigger at all would be
#: an append-only log that is not append-only, which is worse than either state
#: on its own because nothing says so.
WAS_ALLOWED = ("pending>applied", "pending>failed", "pending>rejected")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            "DROP TRIGGER IF EXISTS opt_action_append_only_trg ON opt_action"
        )
        op.execute("UPDATE opt_action SET status = 'pending' WHERE status = 'proposed'")
    op.drop_index("ix_opt_action_expires_at", table_name="opt_action")
    op.drop_index("ix_opt_action_proposed_by", table_name="opt_action")
    op.drop_index("ix_opt_action_risk", table_name="opt_action")
    with op.batch_alter_table("opt_action") as batch:
        batch.drop_column("reverted_at")
        batch.drop_column("expires_at")
        batch.drop_column("window_end")
        batch.drop_column("window_start")
        batch.drop_column("undo_plan")
        batch.drop_column("expected_impact")
        batch.drop_column("proposed_by")
        batch.drop_column("risk")

    if bind.dialect.name != "postgresql":
        return
    # Put the previous revision's trigger back, built from the same generator
    # against the columns that still exist, so the log is append-only again the
    # moment the columns are gone.
    # Put the previous revision's trigger back, built from the same generator
    # against only the columns that still exist, so the log is append-only
    # again the moment the new ones are gone.
    gone = {
        "risk",
        "proposed_by",
        "undo_plan",
        "window_start",
        "window_end",
        "expires_at",
    }
    op.execute(
        sa.text(
            _append_only_sql(
                immutable=tuple(c for c in IMMUTABLE if c not in gone),
                immutable_json=tuple(c for c in IMMUTABLE_JSON if c != "expected_impact"),
                write_once_text=WRITE_ONCE_TEXT,
                write_once_value=tuple(c for c in WRITE_ONCE_VALUE if c != "reverted_at"),
                transitions=WAS_ALLOWED,
            )
        )
    )
    op.execute(_TRIGGER)
