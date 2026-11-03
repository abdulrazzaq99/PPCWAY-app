"""what was asked, what was answered, and what it cost to find out

Revision ID: 7c1d9b4e2af8
Revises: e694ebfaaa03
Create Date: 2026-11-03

Phase 3.2. The brief: *transcripts and tool calls, 12 months, deleted with the
account.* Both halves are here, and the second is done with a foreign key
rather than a job -- a retention promise kept by a nightly sweep is a promise
that breaks the first time the sweep is paused. `ON DELETE CASCADE` from the
organisation means deleting a business takes its transcripts with it as part of
the same statement.

The twelve-month window does need a sweep, because nothing else expires a row
that belongs to a business that still exists. `transcript.forget_old` is it.

**The tool calls are kept, not only the words.** A merchant disputing an answer
is disputing a figure, and the figure came from a lookup. Keeping the reply
without which tools ran and what they returned leaves the one question nobody
can answer afterwards: was the model wrong, or was the mirror?

`cost_usd` is an estimate and is stored rather than computed on read, so a
price change does not rewrite history. It is derived from Anthropic's published
per-token rates, which are **not** the rates this will actually be billed at --
Claude on Vertex AI is partner-operated and priced by Google separately. Until
there is a Google Cloud bill to read, that is the closest honest figure
available, and everything that surfaces it says so.

`account_id` is `ON DELETE SET NULL` rather than cascade: staff leave, and a
business's own transcript should not vanish because the person who typed it no
longer has an account.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "7c1d9b4e2af8"
down_revision = "e694ebfaaa03"
branch_labels = None
depends_on = None

_MINE = "organization_id = NULLIF(current_setting('app.current_org_id', true), '')::uuid"


def upgrade() -> None:
    op.create_table(
        "chat_conversation",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=True),
        sa.Column("customer_id", sa.String(length=20), nullable=False, server_default=""),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("about", sa.String(length=200), nullable=False, server_default=""),
        sa.ForeignKeyConstraint(["organization_id"], ["organization.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["account_id"], ["account.id"], ondelete="SET NULL"),
    )
    op.create_index(
        "ix_chat_conversation_organization_id", "chat_conversation", ["organization_id"]
    )
    op.create_index("ix_chat_conversation_customer_id", "chat_conversation", ["customer_id"])
    op.create_index("ix_chat_conversation_started_at", "chat_conversation", ["started_at"])

    op.create_table(
        "chat_turn",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column(
            "asked_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("question", sa.Text(), nullable=False, server_default=""),
        sa.Column("answer", sa.Text(), nullable=False, server_default=""),
        sa.Column("answer_from", sa.String(length=20), nullable=False, server_default=""),
        sa.Column("tools_used", sa.JSON(), nullable=True),
        sa.Column("figures", sa.JSON(), nullable=True),
        sa.Column("invented", sa.JSON(), nullable=True),
        sa.Column("model", sa.String(length=60), nullable=False, server_default=""),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cached_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("took_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["conversation_id"], ["chat_conversation.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organization.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_chat_turn_conversation_id", "chat_turn", ["conversation_id"])
    op.create_index("ix_chat_turn_organization_id", "chat_turn", ["organization_id"])
    # The spend ceiling reads a month of turns per business, and the retention
    # sweep reads everything older than a year. Both are this index.
    op.create_index("ix_chat_turn_asked_at", "chat_turn", ["asked_at"])

    if op.get_bind().dialect.name != "postgresql":
        return
    for table in ("chat_conversation", "chat_turn"):
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO ppcway_app")
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY {table}_tenant_isolation ON {table}
            USING ({_MINE}) WITH CHECK ({_MINE})
            """
        )


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        for table in ("chat_conversation", "chat_turn"):
            op.execute(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table}")
    op.drop_table("chat_turn")
    op.drop_table("chat_conversation")
