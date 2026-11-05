"""the write gate becomes a switch in the panel, with every flip kept

Revision ID: 4c8d2b6e9f13
Revises: 9e1f5a7c3b20
Create Date: 2026-11-05

Until today the write gate was `ADS_WRITES_ENABLED` and nothing else: turning
writes to Google Ads on or off took a deploy. The owner asked for it in the
admin panel instead -- a redeploy for every flip was the wrong cost for the one
control that gets switched while testing.

`ads_write_gate` holds every flip: on or off, who, when and why. The latest row
is the gate; until there is one, the deployment's setting stands. It is a
record rather than a setting, so the trigger below refuses an update and a
delete, the same as the staff tables: "who turned writes on, and why" has to
survive anybody tidying up.

Platform-wide, like the global kill switch, so there is no tenant column and
no row-level policy. The tenant role may read it and add to it, never more.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "4c8d2b6e9f13"
down_revision = "9e1f5a7c3b20"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ads_write_gate",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("is_open", sa.Boolean(), nullable=False),
        sa.Column("because", sa.Text(), nullable=False, server_default=""),
        sa.Column("set_by", sa.Uuid(), nullable=True),
        sa.Column(
            "set_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index("ix_ads_write_gate_set_at", "ads_write_gate", ["set_at"])

    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("GRANT SELECT, INSERT ON ads_write_gate TO ppcway_app")
    op.execute(
        """
        CREATE OR REPLACE FUNCTION ads_write_gate_append_only() RETURNS trigger AS $fn$
        BEGIN
          IF TG_OP = 'DELETE' THEN
            RAISE EXCEPTION
              'ads_write_gate is a record of who switched writes and rows may not be deleted';
          END IF;
          RAISE EXCEPTION
            'ads_write_gate is a record of who switched writes and rows may not be changed';
        END;
        $fn$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER ads_write_gate_no_changes
          BEFORE UPDATE OR DELETE ON ads_write_gate
          FOR EACH ROW EXECUTE FUNCTION ads_write_gate_append_only()
        """
    )


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS ads_write_gate_no_changes ON ads_write_gate")
        op.execute("DROP FUNCTION IF EXISTS ads_write_gate_append_only()")
    op.drop_index("ix_ads_write_gate_set_at", table_name="ads_write_gate")
    op.drop_table("ads_write_gate")
