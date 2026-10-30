"""the log cannot be rewritten, and a limit version cannot be edited after the fact

Revision ID: d2e3f4a5b6c7
Revises: c1d2e3f4a5b6
Create Date: 2026-10-30

Fix F2 of the client's implementation brief: make the action log append-only
*at the database*, ported from the proof of concept's `0002_audit_spine`.

The models have claimed this property since they were written -- "no update
except the one move from pending to applied, failed or rejected. A log you can
edit is not a log" -- but nothing enforced it. Application convention is not
enforcement: it holds until the first `UPDATE ... SET before = ...` run by hand
against production to tidy something up, and the whole point of an audit spine
is that it answers a dispute months later. A merchant asking "who raised my
budget in March, and on what evidence" is entitled to an answer that nobody
could have quietly changed. So the guarantee belongs where no code path, no
migration shortcut and no psql session can route around it.

**Why this allows some UPDATEs when F2's wording says they must fail.** The
brief's "done when" reads *UPDATE and DELETE on optimization_action fail at the
database*, and taken literally that forbids every update. But the brief's own
specification of the table, two sections later, gives `status` eight values and
columns named `approved by, applied at, reverted at` -- a row whose status
moves, with "a revert is a new row". Those two cannot both be literal: a status
that transitions is an update. So this implements the property the brief is
describing rather than the sentence summarising it, which is also what the
proof of concept did and what Blueprint §8.4 asks for:

  * DELETE always fails. There is no exception and no privileged path.
  * `status` may only follow an enumerated transition, and every terminal
    status is terminal. `applied` never becomes `pending` again.
  * The columns that constitute the evidence may never change at all, on any
    row, in any state -- including `before`, `after`, `evidence` and
    everything identifying which rule and which limits authorised it.
  * The columns that are legitimately filled in later may go from unset to a
    value exactly once, and never change again in either direction. Guarded
    per column rather than as one combined condition, so a first write to one
    cannot be blocked by another already holding a value.

An UPDATE that is not one of those fails at the database. Rewriting history is
what F2 forbids, and that is forbidden absolutely.

`guardrail_config` gets the stricter rule -- no UPDATE at all, no DELETE -- and
needs no transition list, because a limit change is a new version by design.
An action points back at a version to say which limits authorised it, so a
version whose numbers could be edited in place would make every action that
cites it a lie. Nothing in the codebase updates one today, which makes now the
cheapest possible moment to close it.

Postgres only. On SQLite the statements are skipped, so the triggers are the
one thing that cannot be proven by the ordinary suite -- `tests/opt/
test_append_only_db.py` runs against a throwaway Postgres instead, and skips
with a message rather than passing quietly when none is reachable.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "d2e3f4a5b6c7"
down_revision = "c1d2e3f4a5b6"
branch_labels = None
depends_on = None


#: Set when the row is written, never different afterwards. The JSON columns are
#: compared as text: `json` has no equality operator in Postgres, and casting
#: works whichever of `json` or `jsonb` the column turned out to be.
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
    "idempotency_key",
    "undo_of",
    "reversible",
    "created_at",
)
IMMUTABLE_JSON = ("before", "after", "payload", "evidence")

#: Filled in once, during the one transition that sets each, then frozen. Text
#: columns default to '' rather than NULL, so "unset" means either.
WRITE_ONCE_TEXT = ("reason", "decided_by", "decided_because")
WRITE_ONCE_VALUE = ("approved_by", "approved_at", "applied_at")

#: The only moves `status` may make. Every other status is terminal.
TRANSITIONS = ("pending>applied", "pending>failed", "pending>rejected")


def _append_only_sql() -> str:
    """Build the function body. Generated per column, so a refusal names the
    column that caused it: a trigger that says only "something changed" sends
    the next reader to read this file instead of their own stack trace."""
    guards = []
    for column in IMMUTABLE:
        guards.append(
            f"  IF NEW.{column} IS DISTINCT FROM OLD.{column} THEN\n"
            f"    RAISE EXCEPTION 'optimization_action.{column} is evidence and may not change';\n"
            f"  END IF;"
        )
    for column in IMMUTABLE_JSON:
        guards.append(
            f"  IF NEW.{column}::text IS DISTINCT FROM OLD.{column}::text THEN\n"
            f"    RAISE EXCEPTION 'optimization_action.{column} is evidence and may not change';\n"
            f"  END IF;"
        )
    for column in WRITE_ONCE_TEXT:
        guards.append(
            f"  IF COALESCE(OLD.{column}, '') <> ''"
            f" AND NEW.{column} IS DISTINCT FROM OLD.{column} THEN\n"
            f"    RAISE EXCEPTION"
            f" 'optimization_action.{column} was already written and may not change';\n"
            f"  END IF;"
        )
    for column in WRITE_ONCE_VALUE:
        guards.append(
            f"  IF OLD.{column} IS NOT NULL"
            f" AND NEW.{column} IS DISTINCT FROM OLD.{column} THEN\n"
            f"    RAISE EXCEPTION"
            f" 'optimization_action.{column} was already written and may not change';\n"
            f"  END IF;"
        )
    checks = "\n\n".join(guards)
    allowed = ",".join(f"'{t}'" for t in TRANSITIONS)
    return f"""
CREATE OR REPLACE FUNCTION optimization_action_append_only() RETURNS trigger AS $fn$
DECLARE
  allowed text[] := ARRAY[{allowed}];
BEGIN
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION 'optimization_action is append-only: DELETE is forbidden';
  END IF;

  IF NEW.status IS DISTINCT FROM OLD.status
     AND NOT ((OLD.status || '>' || NEW.status) = ANY(allowed)) THEN
    RAISE EXCEPTION
      'optimization_action: % -> % is not an allowed transition', OLD.status, NEW.status;
  END IF;

{checks}

  RETURN NEW;
END;
$fn$ LANGUAGE plpgsql;

CREATE TRIGGER optimization_action_append_only_trg
  BEFORE UPDATE OR DELETE ON optimization_action
  FOR EACH ROW EXECUTE FUNCTION optimization_action_append_only();
"""


GUARDRAIL_IMMUTABLE = """
CREATE OR REPLACE FUNCTION guardrail_config_immutable() RETURNS trigger AS $fn$
BEGIN
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION 'guardrail_config is immutable: DELETE is forbidden';
  END IF;
  RAISE EXCEPTION 'guardrail_config is immutable; write a new version instead';
END;
$fn$ LANGUAGE plpgsql;

CREATE TRIGGER guardrail_config_immutable_trg
  BEFORE UPDATE OR DELETE ON guardrail_config
  FOR EACH ROW EXECUTE FUNCTION guardrail_config_immutable();
"""


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute(sa.text(_append_only_sql()))
    op.execute(sa.text(GUARDRAIL_IMMUTABLE))


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("DROP TRIGGER IF EXISTS guardrail_config_immutable_trg ON guardrail_config")
    op.execute("DROP FUNCTION IF EXISTS guardrail_config_immutable()")
    op.execute("DROP TRIGGER IF EXISTS optimization_action_append_only_trg ON optimization_action")
    op.execute("DROP FUNCTION IF EXISTS optimization_action_append_only()")
