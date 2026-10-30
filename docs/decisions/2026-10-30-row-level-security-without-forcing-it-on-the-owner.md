# Row-level security, enabled but not forced

**Date:** 30 October 2026
**Status:** accepted

## The decision

The seventeen tables covered by `20261030_tenant_isolation.py` get
`ENABLE ROW LEVEL SECURITY` and a policy each. They deliberately do **not** get
`FORCE ROW LEVEL SECURITY`, which the proof of concept's equivalent migration
does apply.

## Why

A policy does not bind the owner of a table. `FORCE` makes it bind the owner
too, which reads like free belt-and-braces. It is not free here, because the
services connect *as* the database owner: on Neon the connecting role owns the
schema and is not a superuser. Under `FORCE`, every one of those seventeen
tables would answer every query that had not set the tenant setting with zero
rows — not an error, an empty result — and the application scopes almost
nothing today. The result would have been a silent, total outage on deploy.

This was measured rather than reasoned about. A non-superuser role was made to
own a table carrying a policy, with no setting present:

```
owner, RLS enabled, no FORCE, no setting -> rows: 2
owner, RLS enabled, WITH FORCE, no setting -> rows: 0
```

The local check had passed before that, because the developer's Postgres user
is a superuser and superusers bypass row-level security unconditionally,
`FORCE` or not. A local run therefore proves nothing about Neon in either
direction, which is worth remembering the next time this area is touched.

## What this costs, honestly

Isolation is enforced for code that reads inside `ppcway.db.session.org_scope`,
which steps down into `ppcway_app` — a role that is neither owner nor
superuser, and so one the policies do bind. Code that does not is protected
only by its own `WHERE organization_id = ...` clauses, exactly as before. That
is the "second wall" the client's brief asks for and no more than that, and
nobody should read "row-level security is on" as meaning the application is
isolated today.

`mail_weekly_post` and `mail_alert_sent` are not covered at all: they are keyed
by person rather than by business, and covering them wants a tenant column
rather than a third shape of join. `account`, `account_link` and
`account_session` are excluded on purpose — a sign-in that had to name a tenant
before it could find one could never happen.

## The end state, and its precondition

`FORCE` is right eventually. Its precondition is that every query touching a
tenant table runs inside `org_scope`. Phases 1 and 2 of the client's brief —
where automated changes to real money are read and written — are written inside
it from the start, so the set of unscoped readers shrinks rather than grows.
Turning `FORCE` on before that is finished converts a leak-shaped risk into an
outage-shaped certainty.

`tests/opt/test_tenant_isolation.py::test_the_application_itself_is_not_blanked_by_the_policies`
exists to fail if somebody adds `FORCE` for tidiness.
