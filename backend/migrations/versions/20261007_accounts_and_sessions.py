"""accounts, sessions, and the audits that belong to them

Signing in with Google creates an account here; the cookie holds a token whose
hash is all this database keeps. An audit run while signed in is kept against the
account, so a person coming back can see what they ran before.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-10-07
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_account",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("google_sub", sa.String(64), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("name", sa.String(200), nullable=False, server_default=""),
        sa.Column("picture", sa.String(500), nullable=False, server_default=""),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_user_account_google_sub", "user_account", ["google_sub"], unique=True)
    op.create_index("ix_user_account_email", "user_account", ["email"])

    op.create_table(
        "user_session",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("user_account.id", name="fk_user_session_user_id"),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_user_session_token_hash", "user_session", ["token_hash"], unique=True)
    op.create_index("ix_user_session_user_id", "user_session", ["user_id"])

    # Batch mode: SQLite cannot ALTER a constraint into place, so Alembic copies the
    # table. On Postgres the same call is a plain ALTER.
    with op.batch_alter_table("audit_request") as batch:
        batch.add_column(sa.Column("user_id", sa.Uuid(), nullable=True))
        batch.create_foreign_key("fk_audit_request_user_id", "user_account", ["user_id"], ["id"])
    op.create_index("ix_audit_request_user_id", "audit_request", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_request_user_id", table_name="audit_request")
    with op.batch_alter_table("audit_request") as batch:
        batch.drop_constraint("fk_audit_request_user_id", type_="foreignkey")
        batch.drop_column("user_id")
    op.drop_table("user_session")
    op.drop_table("user_account")
