"""From a terminal:

`python -m ppcway.cli audit <site>`: run the eight checks and print the report.
`python -m ppcway.cli find "<business name>" ["<town>"]`: list the Google Maps matches.
`python -m ppcway.cli post [--dry]`: the weekly summary. `--dry` prints what each
person would be told and sends nothing, which is how the words get read before a
hundred people read them.
`python -m ppcway.cli gate`: where the phase-one gate stands — seven days of clean
sync on five accounts — counted rather than claimed.
"""

from __future__ import annotations

import json
import sys

from ppcway.ads.gate import gate_report
from ppcway.audit.places import PlacesError, find_businesses
from ppcway.audit.runner import run_audit
from ppcway.config import load_settings
from ppcway.db.session import session_factory
from ppcway.mail.weekly import candidates, post_weekly


def find(name: str, city: str) -> int:
    settings = load_settings()
    if settings.google_maps_api_key is None:
        print("GOOGLE_MAPS_API_KEY is not set in web/.env or backend/.env")
        return 1
    try:
        found = find_businesses(
            name, city=city, api_key=settings.google_maps_api_key.get_secret_value()
        )
    except PlacesError as exc:
        print(exc)
        return 1
    matches = sum(li.name_match for li in found)
    print(f"{len(found)} listings for {name!r} near {city or 'anywhere'}, {matches} with that name")
    for li in found:
        stars = f"{li.rating} from {li.reviews} reviews" if li.rating is not None else "no reviews"
        where = (
            "service area, no address" if li.service_area_only else li.short_address or li.address
        )
        mark = "*" if li.name_match else " "
        print(f"{mark} {li.name}  ·  {li.category or 'no category'}  ·  {where}  ·  {stars}")
        if li.status and li.status != "OPERATIONAL":
            print(f"    {li.status}")
    return 0


def post(dry: bool) -> int:
    """The Monday summary: read it, or send it."""
    settings = load_settings()
    with session_factory()() as session:
        if not dry:
            counts = post_weekly(session, settings)
            print(f"sent {counts['sent']}, failed {counts['failed']}, skipped {counts['skipped']}")
            return 1 if counts["failed"] else 0

        waiting = False
        for who in candidates(session, settings):
            waiting = True
            who_for = who.connection.customer_name or who.connection.customer_id
            if who.letter is None:
                print(f"- {who_for}: no post, {who.skip}")
                continue
            print(f"\n--- {who_for} ---")
            print(f"To: {who.letter.to}")
            print(f"Subject: {who.letter.subject}\n")
            print(who.letter.text)
        if not waiting:
            print(
                "Nothing to send: either no account is connected, or every one "
                "already has this week's post."
            )
    return 0


def gate() -> int:
    """Where the phase-one gate stands, account by account."""
    with session_factory()() as session:
        standing = gate_report(session)
    print(standing.said)
    print()
    for account in standing.accounts:
        mark = "pass" if account.passing else "    "
        print(
            f"{mark}  {account.name or account.customer_id:<24} "
            f"{account.clean_days}/{standing.days} clean days, {account.runs} runs"
        )
        if account.silent_days:
            print(f"        no read at all on: {', '.join(account.silent_days)}")
        if account.failed_days:
            print(f"        failed on: {', '.join(account.failed_days)}")
        if account.trouble:
            print(f"        {account.trouble}")
    return 0 if standing.passed else 1


def staff(email: str, level: str, because: str) -> int:
    """Give somebody internal access, or take it away.

    Here rather than as an endpoint because of the bootstrap problem: only a
    principal may grant staff access, and a fresh deployment has no principal
    to do it. An endpoint that solved that would be an endpoint that can create
    a principal without one -- a back door, however carefully it is gated. A
    command needs the database URL, and whoever holds that needs no back door.

    An empty level withdraws. The reason is required either way, because
    `staff_grant` exists to be read back and a row that does not say why
    cannot be.
    """
    from sqlalchemy import func, select

    from ppcway.auth.models import UserAccount
    from ppcway.db.session import session_factory
    from ppcway.staff.guard import grant, level_of, withdraw
    from ppcway.staff.models import Level

    wanted = (level or "").strip().lower()
    known = ", ".join(one.value for one in Level)
    if wanted and wanted not in {one.value for one in Level}:
        print(f"level must be one of: {known} (or empty to withdraw)")
        return 2
    if not (because or "").strip():
        print('say why: --because "the reason this access was given"')
        return 2

    with session_factory()() as session:
        account = session.scalars(
            select(UserAccount).where(func.lower(UserAccount.email) == email.strip().lower())
        ).first()
        if account is None:
            print(
                f"nobody has signed in as {email}. They have to sign in once first --"
                f" a grant points at an account, and there is no account yet."
            )
            return 1
        if not wanted:
            gone = withdraw(session, account_id=account.id, by_account_id=None, because=because)
            session.commit()
            print(f"{email} no longer has access." if gone else f"{email} had no access.")
            return 0
        grant(
            session,
            account_id=account.id,
            level=Level(wanted),
            # No granter recorded: this is the bootstrap path, and a false one
            # would be worse than none.
            by_account_id=None,
            because=because,
        )
        session.commit()
        held = level_of(session, account)
        print(f"{email} now has {held.value if held else 'no'} access.")
    return 0


def main(argv: list[str]) -> int:
    if argv and argv[0] == "gate":
        return gate()
    if argv and argv[0] == "staff":
        rest = argv[1:]
        if not rest:
            print('usage: python -m ppcway.cli staff <email> <level> --because "why"')
            print("       level: support, engineer, principal, or omitted to withdraw")
            return 2
        wanted_level = rest[1] if len(rest) > 1 and not rest[1].startswith("--") else ""
        reason = ""
        if "--because" in rest:
            reason = " ".join(rest[rest.index("--because") + 1 :])
        return staff(rest[0], wanted_level, reason)
    if argv and argv[0] == "post":
        return post("--dry" in argv)
    if len(argv) >= 2 and argv[0] == "find":
        return find(argv[1], argv[2] if len(argv) > 2 else "")
    if len(argv) < 2 or argv[0] != "audit":
        print(
            "usage: python -m ppcway.cli audit <site> [--json]\n"
            '       python -m ppcway.cli find "<name>" ["<town>"]\n'
            "       python -m ppcway.cli post [--dry]\n"
            "       python -m ppcway.cli gate\n"
            '       python -m ppcway.cli staff <email> <level> --because "why"'
        )
        return 2
    report = run_audit(argv[1], load_settings())
    if "--json" in argv:
        print(json.dumps(report.as_dict(), indent=2))
        return 0
    took = (report.finished_at - report.started_at).total_seconds() if report.finished_at else 0
    print(f"{report.site}  {report.pages_read} pages  {took:.0f}s  {report.counts}")
    for f in report.findings:
        print(f"\n[{f.status:9}] {f.title}\n  {f.summary}")
        for d in f.detail:
            print(f"    - {d}")
        if f.fix:
            print(f"  Fix: {f.fix}")
    for n in report.notes:
        print(f"\nnote: {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
