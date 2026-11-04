"""Find, and optionally remove, a business that was created for a staff account.

`home_for` used to create a business named after the email the first time
somebody opened the app, so signing in as a PPCWay staff account silently made
a merchant out of it. That is fixed in the code; this clears up the one that
already exists.

    python scripts/stray_staff_org.py                 # show what it would touch
    python scripts/stray_staff_org.py --remove        # actually remove it
    python scripts/stray_staff_org.py --audit         # every account with more than one
    python scripts/stray_staff_org.py --dedupe        # show the extras the race left
    python scripts/stray_staff_org.py --dedupe --remove

`--audit` exists because the stray staff business turned out to be two, and
two was a race in `home_for` rather than anything to do with staff: a first
page load fires several calls at once and each made a business. That is fixed,
but any account that signed up before the fix may be carrying duplicates.
`--audit` only reads.

Shows first and removes only when asked, because the query joins on an email
and a wrong email would name somebody's real business. Read the list before
passing --remove.

It refuses to remove a business that has anything in it: another member, a
Google Ads connection, or any proposed change. A staff account's accidental
business is empty by definition, so anything else is not the row this is for.
"""

from __future__ import annotations

import os
import sys

import sqlalchemy as sa

STAFF_EMAIL = "admin@ppcway.com"

FIND = sa.text("""
    select o.id, o.name, o.created_at,
           (select count(*) from membership m2 where m2.organization_id = o.id) as people,
           (select count(*) from ads_connection c where c.organization_id = o.id) as connections,
           (select count(*) from opt_action a2 where a2.organization_id = o.id) as changes
      from organization o
      join membership m on m.organization_id = o.id
      join account a on a.id = m.account_id
     where lower(a.email) = lower(:email)
""")


DUPLICATES = sa.text("""
    select a.email,
           count(distinct o.id) as businesses,
           sum(case when (select count(*) from ads_connection c
                           where c.organization_id = o.id) = 0
                     and (select count(*) from opt_action x
                           where x.organization_id = o.id) = 0
                    then 1 else 0 end) as empty_ones
      from account a
      join membership m on m.account_id = a.id
      join organization o on o.id = m.organization_id
     group by a.email
    having count(distinct o.id) > 1
     order by count(distinct o.id) desc
""")


def audit(url: str) -> int:
    """Every account holding more than one business. Reads only."""
    engine = sa.create_engine(url)
    with engine.connect() as c:
        rows = c.execute(DUPLICATES).all()
    if not rows:
        print("no account holds more than one business. Nothing to clean up.")
        return 0
    print(f"{len(rows)} account(s) hold more than one business:\n")
    for row in rows:
        print(f"  {row.email}  businesses={row.businesses}  of which empty={row.empty_ones}")
    print(
        "\nAn account with two businesses where one is empty is almost certainly the"
        "\nrace. One with two that both have data is a person who really runs two,"
        "\nand must be left alone."
    )
    return 0


MINE = sa.text("""
    select o.id, o.name, m.created_at,
           (select count(*) from ads_connection c where c.organization_id = o.id) as connections,
           (select count(*) from opt_action x where x.organization_id = o.id) as changes,
           (select count(*) from membership m2 where m2.organization_id = o.id) as people
      from organization o
      join membership m on m.organization_id = o.id
      join account a on a.id = m.account_id
     where lower(a.email) = lower(:email)
     order by m.created_at asc
""")


def dedupe(url: str, *, remove: bool) -> int:
    """Drop the extra empty businesses the race left, keeping the one in use.

    The oldest membership is kept, because that is the one `home_for` returns
    and therefore the one the person has been using. Everything newer is
    removed only if it is genuinely empty: no connection, no changes, nobody
    else in it. A duplicate that acquired data is not a duplicate any more.
    """
    engine = sa.create_engine(url)
    with engine.begin() as c:
        emails = [row.email for row in c.execute(DUPLICATES).all()]
        if not emails:
            print("no account holds more than one business. Nothing to do.")
            return 0

        going: list[tuple[str, str, str]] = []
        for email in emails:
            rows = c.execute(MINE, {"email": email}).all()
            keeping, rest = rows[0], rows[1:]
            print(f"{email}")
            print(f"  keep    {keeping.name!r}  (oldest, the one the app uses)")
            for row in rest:
                empty = row.connections == 0 and row.changes == 0 and row.people <= 1
                print(
                    f"  {'remove ' if empty else 'KEEP   '} {row.name!r}"
                    f"  connections={row.connections} changes={row.changes}"
                    f" people={row.people}"
                    f"{'' if empty else '  <- has something in it, left alone'}"
                )
                if empty:
                    going.append((email, str(row.id), row.name))
            print()

        if not going:
            print("nothing is empty enough to remove.")
            return 0
        if not remove:
            print(f"{len(going)} would be removed. Re-run with --remove to do it.")
            return 0
        for _email, one, _name in going:
            c.execute(sa.text("delete from membership where organization_id = :id"), {"id": one})
            c.execute(sa.text("delete from organization where id = :id"), {"id": one})
        print(f"removed {len(going)}.")
    return 0


def main() -> int:
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("set DATABASE_URL first")
        return 2
    if "--audit" in sys.argv:
        return audit(url)
    if "--dedupe" in sys.argv:
        return dedupe(url, remove="--remove" in sys.argv)
    email = os.environ.get("STAFF_EMAIL", STAFF_EMAIL)
    remove = "--remove" in sys.argv

    engine = sa.create_engine(url)
    with engine.begin() as c:
        rows = c.execute(FIND, {"email": email}).all()
        if not rows:
            print(f"nothing found for {email}. Either it was never created or it is gone.")
            return 0

        print(f"businesses attached to {email}:\n")
        removable = []
        for row in rows:
            empty = row.people <= 1 and row.connections == 0 and row.changes == 0
            print(
                f"  {row.name!r}  id={row.id}  people={row.people}"
                f"  connections={row.connections}  changes={row.changes}"
                f"  {'<- empty, safe to remove' if empty else '<- NOT empty, left alone'}"
            )
            if empty:
                removable.append(row.id)

        if not remove:
            print(f"\n{len(removable)} removable. Re-run with --remove to do it.")
            return 0
        if not removable:
            print("\nnothing is empty enough to remove. Nothing done.")
            return 0

        for one in removable:
            c.execute(sa.text("delete from membership where organization_id = :id"), {"id": one})
            c.execute(sa.text("delete from organization where id = :id"), {"id": one})
        print(f"\nremoved {len(removable)}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
