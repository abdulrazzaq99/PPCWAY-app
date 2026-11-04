"""Find, and optionally remove, a business that was created for a staff account.

`home_for` used to create a business named after the email the first time
somebody opened the app, so signing in as a PPCWay staff account silently made
a merchant out of it. That is fixed in the code; this clears up the one that
already exists.

    python scripts/stray_staff_org.py                 # show what it would touch
    python scripts/stray_staff_org.py --remove        # actually remove it

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


def main() -> int:
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("set DATABASE_URL first")
        return 2
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
