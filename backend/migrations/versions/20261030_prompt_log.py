"""what we asked a model, with the people taken out, kept thirty days

Revision ID: f4a5b6c7d8e9
Revises: e3f4a5b6c7d8
Create Date: 2026-10-30

Phase 0.2's half of the model service that outlives a process: the redacted
prompt log the client's brief asks for, and which Anthropic's own guidance for
Claude on Vertex recommends for the same thirty days.

No foreign key to `organization`, deliberately. An internal job may have no
organisation at all, and a row here has to survive the account it was about
being deleted -- the question this table answers, "what was this model asked
to do", is asked after the fact and sometimes about an account that is gone.
A foreign key would either block that deletion or cascade away the evidence.

Not covered by the row-level security of the previous migration, for the same
reason: it is not a tenant table, it is an operational record about the
platform, and the organisation on it is a label rather than an owner. Nothing
merchant-facing reads it.

The text columns hold redacted text -- see `ppcway.model.redact` -- because a
redaction applied on the way out is a redaction that was never applied to the
backup, the replica or the log shipper.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "f4a5b6c7d8e9"
down_revision = "e3f4a5b6c7d8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "model_prompt_log",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("customer_id", sa.String(length=20), nullable=False, server_default=""),
        sa.Column("job", sa.String(length=30), nullable=False),
        sa.Column("model", sa.String(length=60), nullable=False),
        sa.Column("prompt_version", sa.String(length=30), nullable=False),
        sa.Column("system_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("input_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("output_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("stop_reason", sa.String(length=30), nullable=False, server_default=""),
        sa.Column("armor", sa.String(length=20), nullable=False, server_default="not_screened"),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cached_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("took_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("trouble", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_model_prompt_log_organization_id", "model_prompt_log", ["organization_id"])
    op.create_index("ix_model_prompt_log_customer_id", "model_prompt_log", ["customer_id"])
    op.create_index("ix_model_prompt_log_job", "model_prompt_log", ["job"])
    # The retention job deletes by age, and it is the only query that matters
    # for how big this table gets.
    op.create_index("ix_model_prompt_log_created_at", "model_prompt_log", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_model_prompt_log_created_at", table_name="model_prompt_log")
    op.drop_index("ix_model_prompt_log_job", table_name="model_prompt_log")
    op.drop_index("ix_model_prompt_log_customer_id", table_name="model_prompt_log")
    op.drop_index("ix_model_prompt_log_organization_id", table_name="model_prompt_log")
    op.drop_table("model_prompt_log")
