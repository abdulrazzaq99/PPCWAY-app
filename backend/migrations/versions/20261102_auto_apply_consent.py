"""what somebody agreed to when they let Otto act without asking

Revision ID: a1b2c3d4e5f6
Revises: f0a1b2c3d4e5
Create Date: 2026-11-02

Phase 2.4. The client's brief specifies the record's fields, and the fields
are the specification: *account, user (owner only), timestamp, IP, consent
wording version, change types, limits.* Each one answers a question somebody
asks later, and "they agreed" answers none of them.

The wording version and the words themselves are both kept. The version
identifies what was agreed; the text is what was agreed, because a dispute six
months from now is not helped by an identifier whose words nobody kept. The
change types and the limits are snapshotted for the same reason -- adding a
rule to the eligible list must not widen a permission given last March, and
somebody who agreed while the cap was 20% did not agree to 50%.

Withdrawing does not delete the row. That somebody once agreed, when, and to
what is the record; a new permission is a new row, and only one may be live.

Covered by row-level security like every other per-business table: a consent
record is the most sensitive row in the schema after the credential itself,
because it is the one that says money may move without anybody being asked.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# A random id rather than the next step of the rotating hex pattern the earlier
# migrations use: that pattern has come all the way round, and "a1b2c3d4e5f6"
# is already the September audit-tables revision. Alembic answers a reused id
# with `CycleDetected` across the whole chain, which is a confusing way to be
# told about a name collision -- so from here the ids are random.
revision = "e694ebfaaa03"
down_revision = "f0a1b2c3d4e5"
branch_labels = None
depends_on = None

_MINE = "organization_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid"


def upgrade() -> None:
    op.create_table(
        "opt_auto_apply_consent",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column(
            "given_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("ip", sa.String(length=45), nullable=False, server_default=""),
        sa.Column("wording", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("words", sa.Text(), nullable=False, server_default=""),
        sa.Column("change_types", sa.JSON(), nullable=True),
        sa.Column("limits", sa.JSON(), nullable=True),
        sa.Column("withdrawn_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("withdrawn_by", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organization.id"]),
        sa.ForeignKeyConstraint(["account_id"], ["account.id"]),
        sa.ForeignKeyConstraint(["withdrawn_by"], ["account.id"]),
    )
    op.create_index(
        "ix_opt_auto_apply_consent_organization_id",
        "opt_auto_apply_consent",
        ["organization_id"],
    )
    op.create_index("ix_opt_auto_apply_consent_given_at", "opt_auto_apply_consent", ["given_at"])

    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON opt_auto_apply_consent TO ppcway_app")
    op.execute("ALTER TABLE opt_auto_apply_consent ENABLE ROW LEVEL SECURITY")
    op.execute(
        f"""
        CREATE POLICY opt_auto_apply_consent_tenant_isolation ON opt_auto_apply_consent
        USING ({_MINE}) WITH CHECK ({_MINE})
        """
    )


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            "DROP POLICY IF EXISTS opt_auto_apply_consent_tenant_isolation"
            " ON opt_auto_apply_consent"
        )
    op.drop_table("opt_auto_apply_consent")
