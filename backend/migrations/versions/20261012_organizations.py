"""Organisations, who is in them, and what each person may do.

The requirements are explicit that plan limits and roles are enforced in the
backend rather than hidden in the interface, so this is the table every
endpoint will ask before it does anything.

Existing accounts are each given a business of their own, owned by them, and
their Google Ads connections and audits move with them. Nobody loses anything.

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "c9d0e1f2a3b4"
down_revision = "b8c9d0e1f2a3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "organization",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("plan", sa.String(20), nullable=False, server_default="starter"),
        sa.Column("country", sa.String(2), nullable=False, server_default="CA"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="CAD"),
        sa.Column("billing_customer", sa.String(80), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "membership",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organization.id"), nullable=False),
        sa.Column("account_id", sa.Uuid(), sa.ForeignKey("account.id"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="owner"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("organization_id", "account_id", name="one_place_each"),
    )
    op.create_index("ix_membership_organization_id", "membership", ["organization_id"])
    op.create_index("ix_membership_account_id", "membership", ["account_id"])

    op.create_table(
        "membership_invite",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organization.id"), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="member"),
        sa.Column("invited_by", sa.Uuid(), sa.ForeignKey("account.id"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_membership_invite_email", "membership_invite", ["email"])
    op.create_index("ix_membership_invite_token_hash", "membership_invite", ["token_hash"])

    # What belongs to a business rather than to a person.
    with op.batch_alter_table("ads_connection") as batch:
        batch.add_column(sa.Column("organization_id", sa.Uuid(), nullable=True))
    with op.batch_alter_table("audit_request") as batch:
        batch.add_column(sa.Column("organization_id", sa.Uuid(), nullable=True))

    # Everybody who already signed in gets a business of one, owned by them.
    bind = op.get_bind()
    people = bind.execute(sa.text("SELECT id, email, name FROM account")).fetchall()
    for account_id, email, name in people:
        new_id = _fresh(bind)
        label = (name or (email or "").split("@")[0] or "My business")[:200]
        bind.execute(
            sa.text(
                "INSERT INTO organization (id, name, plan, country, currency, billing_customer)"
                " VALUES (:i, :n, 'starter', 'CA', 'CAD', '')"
            ),
            {"i": new_id, "n": label},
        )
        bind.execute(
            sa.text(
                "INSERT INTO membership (id, organization_id, account_id, role)"
                " VALUES (:m, :o, :a, 'owner')"
            ),
            {"m": _fresh(bind), "o": new_id, "a": account_id},
        )
        bind.execute(
            sa.text("UPDATE ads_connection SET organization_id = :o WHERE account_id = :a"),
            {"o": new_id, "a": account_id},
        )
        bind.execute(
            sa.text("UPDATE audit_request SET organization_id = :o WHERE user_id = :a"),
            {"o": new_id, "a": account_id},
        )


def _fresh(bind: sa.engine.Connection) -> object:
    if bind.dialect.name == "postgresql":
        return bind.execute(sa.text("SELECT gen_random_uuid()")).scalar()
    import uuid as _uuid

    return _uuid.uuid4()


def downgrade() -> None:
    with op.batch_alter_table("audit_request") as batch:
        batch.drop_column("organization_id")
    with op.batch_alter_table("ads_connection") as batch:
        batch.drop_column("organization_id")
    op.drop_table("membership_invite")
    op.drop_table("membership")
    op.drop_table("organization")
