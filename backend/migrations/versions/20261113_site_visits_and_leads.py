"""the merchant's website: the script key, visits, and leads

Revision ID: 8e4c6f3b1d52
Revises: 7d3b5e2a9c41
Create Date: 2026-11-13

The PPCWay script on a merchant's website reports visits and leads; a lead the
merchant marks as a job is sent to Google Ads against its ad click. See
`ppcway.site`.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "8e4c6f3b1d52"
down_revision = "7d3b5e2a9c41"
branch_labels = None
depends_on = None


def _json() -> sa.types.TypeEngine[object]:
    return sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "site_key",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=40), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_url", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("send_jobs", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("job_action", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("form_send_to", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("call_send_to", sa.String(length=100), nullable=False, server_default=""),
        sa.ForeignKeyConstraint(["organization_id"], ["organization.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_site_key_organization_id", "site_key", ["organization_id"], unique=True)
    op.create_index("ix_site_key_key", "site_key", ["key"], unique=True)

    op.create_table(
        "site_visit",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("visit", sa.String(length=40), nullable=False),
        sa.Column("visitor", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("landing", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("referrer", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("source", sa.String(length=20), nullable=False, server_default="direct"),
        sa.Column("campaign", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("gclid", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("gbraid", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("wbraid", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("device", sa.String(length=10), nullable=False, server_default=""),
        sa.Column("views", sa.Integer(), nullable=False, server_default="1"),
        sa.ForeignKeyConstraint(["organization_id"], ["organization.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "visit", name="uq_site_visit_visit"),
    )
    op.create_index("ix_site_visit_organization_id", "site_visit", ["organization_id"])
    op.create_index("ix_site_visit_started_at", "site_visit", ["started_at"])

    op.create_table(
        "site_lead",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("visit_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("kind", sa.String(length=10), nullable=False),
        sa.Column("page", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("form", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("fields", _json(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("email", sa.String(length=320), nullable=False, server_default=""),
        sa.Column("phone", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("source", sa.String(length=20), nullable=False, server_default="direct"),
        sa.Column("campaign", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("gclid", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("gbraid", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("wbraid", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("clicked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sender", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=10), nullable=False, server_default="new"),
        sa.Column("value", sa.Float(), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default=""),
        sa.Column("marked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("marked_by", sa.Uuid(), nullable=True),
        sa.Column("upload", sa.String(length=10), nullable=False, server_default=""),
        sa.Column("upload_note", sa.String(length=300), nullable=False, server_default=""),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organization.id"]),
        sa.ForeignKeyConstraint(["visit_id"], ["site_visit.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["marked_by"], ["account.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_site_lead_organization_id", "site_lead", ["organization_id"])
    op.create_index("ix_site_lead_created_at", "site_lead", ["created_at"])
    op.create_index("ix_site_lead_sender", "site_lead", ["sender"])


def downgrade() -> None:
    op.drop_table("site_lead")
    op.drop_table("site_visit")
    op.drop_table("site_key")
