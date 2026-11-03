"""who works for PPCWay, and the record of what they looked at

Two tables, both append-only, and the triggers say so rather than the
documentation. A grant is given by writing a row and taken away by writing
another; a look is written once and never touched. "Who could see this account
in March" is a question somebody will eventually have to answer, and a table
that can be updated cannot answer it.

Revision ID: b4f81c6d2e07
Revises: 7c1d9b4e2af8
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "b4f81c6d2e07"
down_revision = "7c1d9b4e2af8"
branch_labels = None
depends_on = None

#: Both tables are wholly immutable once written, so there is no column list to
#: keep in step with a model -- any UPDATE at all is refused. That is a
#: stronger and simpler guarantee than the action log's, which has to allow a
#: status to move.
TABLES = ("staff_grant", "staff_look")


def _refuse_changes(table: str) -> str:
    return f"""
CREATE OR REPLACE FUNCTION {table}_append_only() RETURNS trigger AS $fn$
BEGIN
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION
      '{table} is a record of who saw what and rows may not be deleted';
  END IF;
  RAISE EXCEPTION
    '{table} is a record of who saw what and rows may not be changed';
END;
$fn$ LANGUAGE plpgsql;

CREATE TRIGGER {table}_no_changes
  BEFORE UPDATE OR DELETE ON {table}
  FOR EACH ROW EXECUTE FUNCTION {table}_append_only();
"""


def upgrade() -> None:
    op.create_table(
        "staff_grant",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "account_id",
            sa.Uuid(),
            sa.ForeignKey("account.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("level", sa.String(length=20), nullable=False),
        sa.Column("granted", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "by_account_id",
            sa.Uuid(),
            sa.ForeignKey("account.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("because", sa.Text(), nullable=False, server_default=""),
        sa.Column("at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_staff_grant_account_id", "staff_grant", ["account_id"])
    # The current level is "the latest row for this account", which is read on
    # every single internal request. Without this it is a scan of the whole
    # table each time.
    op.create_index("ix_staff_grant_account_at", "staff_grant", ["account_id", "at"])

    op.create_table(
        "staff_look",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "account_id",
            sa.Uuid(),
            sa.ForeignKey("account.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            sa.Uuid(),
            sa.ForeignKey("organization.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("organization_name", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("looked_at", sa.String(length=40), nullable=False, server_default="merchant"),
        sa.Column("level", sa.String(length=20), nullable=False, server_default="support"),
        sa.Column("at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_staff_look_account_id", "staff_look", ["account_id"])
    # So a merchant can be shown who looked at them, newest first.
    op.create_index("ix_staff_look_org_at", "staff_look", ["organization_id", "at"])

    # SQLite has no triggers of this shape and no plpgsql. The tests that prove
    # the wall works run against Postgres; the SQLite suite proves the
    # application does not try to update these rows in the first place.
    if op.get_bind().dialect.name != "postgresql":
        return
    for table in TABLES:
        op.execute(sa.text(_refuse_changes(table)))


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        for table in TABLES:
            op.execute(sa.text(f"DROP TRIGGER IF EXISTS {table}_no_changes ON {table}"))
            op.execute(sa.text(f"DROP FUNCTION IF EXISTS {table}_append_only()"))
    op.drop_index("ix_staff_look_org_at", table_name="staff_look")
    op.drop_index("ix_staff_look_account_id", table_name="staff_look")
    op.drop_table("staff_look")
    op.drop_index("ix_staff_grant_account_at", table_name="staff_grant")
    op.drop_index("ix_staff_grant_account_id", table_name="staff_grant")
    op.drop_table("staff_grant")
