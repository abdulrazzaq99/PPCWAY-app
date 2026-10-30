"""one organisation cannot read another, enforced by Postgres and not by us

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
Create Date: 2026-10-30

Fix F1 of the client's implementation brief: Postgres row-level security for
tenant isolation, ported from the proof of concept's `0001_core_schema`. The
brief is explicit that the application's own `WHERE organization_id = ...`
clauses stay. This is the second wall, not a replacement for the first: a
forgotten WHERE becomes a query that returns nothing, instead of one business
reading another's spend.

**What this does and does not change today.** Row-level security binds the role
a statement runs as. The services connect as the database owner, and a policy
does not apply to a table's owner, so nothing in the running app changes
behaviour the moment this migration lands. A code path becomes protected once
it reads inside `ppcway.db.session.org_scope`, which steps down into
`ppcway_app` -- a role that is neither the owner nor a superuser, and therefore
one the policies do bind. That is deliberate: a migration that silently
changed what every existing endpoint could see would be the wrong way to
introduce this. It does also mean the wall protects what has been moved behind
it and no more. The brief's phases 1 and 2, where automated changes to real
money are read and written, are written inside it from the start.

**Why these tables are NOT `FORCE ROW LEVEL SECURITY`, when the proof of
concept's are.** FORCE makes the policies apply to the table owner as well.
That reads like free belt-and-braces and is not: on Neon the role the services
connect as is the database owner and is not a superuser, so under FORCE every
one of the seventeen tables below would answer every unscoped query with zero
rows. Not an error -- an empty result. The whole application, which today
scopes almost nothing, would come up blank on deploy.

This was measured, not reasoned about. A non-superuser role was made to own a
table with a policy and no setting present: with RLS enabled it read its two
rows, and the moment FORCE was added it read none. The check passed locally
before that because the developer's Postgres user is a superuser, and
superusers bypass row-level security unconditionally, FORCE or not -- so the
local run proves nothing about Neon either way.

FORCE is the right end state, and it is a milestone with a precondition:
every query that touches a tenant table runs inside `org_scope`. Until then
it would convert a leak-shaped risk into an outage-shaped certainty.

**`ppcway_app` is NOLOGIN, and granted to whoever connects.** Nothing ever
connects as it directly; a login role steps down into it per transaction.
The grant at the end is the proof of concept's migration 0011, folded in here
rather than learned again: on Neon the connecting role is not a superuser and
cannot `SET ROLE` to a role it is not a member of, so without the grant the
first scoped write dies with `InsufficientPrivilege: permission denied to set
role "ppcway_app"`. Fail-closed is the right direction for a security control
and this is what it looks like from outside: a 500 on every write.
`current_user`, not a hard-coded name, because the name is the provider's to
choose.

**Three shapes of policy, because the tables are keyed three ways.**

  * `organization` is scoped by its own `id`.
  * Seven tables carry `organization_id` and compare it directly. On three of
    them that column is nullable; a row with no organisation is visible to no
    organisation, which is the fail-closed answer and the right one. An
    anonymous free audit is exactly such a row, and the public endpoints that
    read it do not run inside `org_scope`.
  * The seven mirror tables carry only `customer_id`, Google's own account
    number, so they reach their tenant through `ads_connection`. A subquery in
    a policy costs more than a column would, and the alternative -- adding
    `organization_id` to every mirror table -- was rejected because it makes
    isolation depend on every future write path remembering to set it. The
    subquery cannot be forgotten. Postgres plans it as a semi-join, and both
    sides are indexed. The subquery is itself subject to the policy on
    `ads_connection`, which gives the same answer by a second route.
  * `audit_run` and `audit_email_code` reach their tenant through
    `audit_request` the same way.

**What is deliberately NOT covered, and why.** `account`, `account_link` and
`account_session` hold people, not tenant data, and are read before any
organisation is known -- a sign-in that had to name a tenant first could never
happen. `ads_consent_trip` is an OAuth trip in flight, keyed by the person.
`mail_weekly_post` and `mail_alert_sent` are keyed by the person too; they are
the one real gap here, and closing it wants a tenant column on both rather
than a third join shape. None of these is covered by this migration, and a
reader should not take "row-level security is on" to mean otherwise.
"""

from __future__ import annotations

from alembic import op

revision = "e3f4a5b6c7d8"
down_revision = "d2e3f4a5b6c7"
branch_labels = None
depends_on = None


#: The setting a scoped transaction writes, read back by every policy below.
#: `NULLIF(..., '')` turns an unset or cleared setting into NULL, and NULL
#: compares to nothing, so an unscoped statement sees no rows rather than all
#: of them. That is the fail-closed half, and it is load-bearing.
GUC = "app.current_org_id"
ORG = f"NULLIF(current_setting('{GUC}', true), '')::uuid"

#: Tables with the tenant on the row.
DIRECT = (
    "membership",
    "membership_invite",
    "ads_connection",
    "audit_request",
    "share_link",
    "guardrail_config",
    "optimization_action",
)

#: Tables that reach the tenant through the connection that owns the account
#: number they are keyed by.
VIA_CUSTOMER = (
    "ads_campaign",
    "ads_ad_group",
    "ads_keyword",
    "ads_ad",
    "ads_campaign_day",
    "ads_sync_run",
    "ads_external_change",
)

#: Tables that reach the tenant through the audit they belong to.
VIA_AUDIT = {"audit_run": "request_id", "audit_email_code": "request_id"}

ALL_COVERED = ("organization", *DIRECT, *VIA_CUSTOMER, *VIA_AUDIT)

_CUSTOMER_OF_ORG = (
    f"customer_id IN (SELECT customer_id FROM ads_connection"
    f" WHERE organization_id = {ORG} AND customer_id <> '')"
)


def _audit_of_org(column: str) -> str:
    return f"{column} IN (SELECT id FROM audit_request WHERE organization_id = {ORG})"


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    # Guarded: roles are cluster-wide and survive a DROP TABLE, so an upgrade
    # run after a downgrade/upgrade cycle must not fail on a role still there.
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'ppcway_app') THEN
                CREATE ROLE ppcway_app NOLOGIN;
            END IF;
        END
        $$;
        """
    )
    op.execute("GRANT USAGE ON SCHEMA public TO ppcway_app")
    # Every primary key defaults to a client-side uuid4 rather than a database
    # sequence, so this grants nothing today. It is here so that adding a
    # sequence later does not fail inside a scoped transaction.
    op.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO ppcway_app")

    for table in ALL_COVERED:
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO ppcway_app")
        # ENABLE, and deliberately not FORCE: see the note at the top of this
        # file. FORCE would bind the owner, which is the role the services
        # connect as, and blank the application.
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")

    op.execute(
        f"""
        CREATE POLICY organization_tenant_isolation ON organization
        USING (id = {ORG}) WITH CHECK (id = {ORG})
        """
    )
    for table in DIRECT:
        op.execute(
            f"""
            CREATE POLICY {table}_tenant_isolation ON {table}
            USING (organization_id = {ORG}) WITH CHECK (organization_id = {ORG})
            """
        )
    for table in VIA_CUSTOMER:
        op.execute(
            f"""
            CREATE POLICY {table}_tenant_isolation ON {table}
            USING ({_CUSTOMER_OF_ORG}) WITH CHECK ({_CUSTOMER_OF_ORG})
            """
        )
    for table, column in VIA_AUDIT.items():
        clause = _audit_of_org(column)
        op.execute(
            f"""
            CREATE POLICY {table}_tenant_isolation ON {table}
            USING ({clause}) WITH CHECK ({clause})
            """
        )

    # A connection written before organisations existed, or by a deploy that
    # raced the one that added the column, would be invisible to its own
    # business under the policy above -- and, since F3, invisible to the
    # application too. Belt and braces for the 12 October backfill.
    op.execute(
        """
        UPDATE ads_connection AS c SET organization_id = m.organization_id
        FROM membership AS m
        WHERE c.organization_id IS NULL AND m.account_id = c.account_id
        """
    )

    # The proof of concept's 0011, folded in: see the note at the top.
    op.execute(
        """
        DO $$
        BEGIN
            EXECUTE format('GRANT ppcway_app TO %I', current_user);
        END
        $$;
        """
    )


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    for table in ALL_COVERED:
        op.execute(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
        op.execute(f"REVOKE ALL ON {table} FROM ppcway_app")
    # The role itself is left in place: it is cluster-wide, other databases in
    # the same cluster may be using it, and dropping it is not this migration's
    # business.
