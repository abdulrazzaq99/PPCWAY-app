"""The internal panel's routes, and who gets through them.

The gating is the whole point of this file. Every route is staff-only, the
refusal is the same shape for a stranger and for staff at too low a level, and
opening a named business leaves a record. A merchant's own admin -- `Role.ADMIN`
-- must get nothing, and that is tested through the HTTP layer as well as the
guard, because the guard being right does not prove the endpoint calls it.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator

import pytest
import sqlalchemy as sa
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from ppcway.api.app import create_app
from ppcway.auth.models import UserAccount
from ppcway.auth.sessions import sign_in_existing
from ppcway.config import Settings
from ppcway.db.base import Base
from ppcway.db.session import get_session
from ppcway.org.models import Role
from ppcway.org.places import accept, home_for, invite
from ppcway.staff.guard import grant
from ppcway.staff.models import Level, StaffLook

EVERY_ROUTE = (
    ("GET", "/v1/admin/overview"),
    ("GET", "/v1/admin/merchants"),
    ("GET", "/v1/admin/platform"),
    ("GET", "/v1/admin/quota?customer_id=123"),
    ("GET", "/v1/admin/staff"),
    ("POST", "/v1/admin/platform/stop"),
    ("POST", "/v1/admin/platform/release"),
    ("POST", "/v1/admin/staff"),
)


def _world(**over: object) -> Iterator[tuple[FastAPI, sessionmaker[Session]]]:
    engine = sa.create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=sa.pool.StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    app = create_app(Settings(environment="test", **over))  # type: ignore[arg-type]

    def one_session() -> Iterator[Session]:
        session = factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_session] = one_session
    yield app, factory
    Base.metadata.drop_all(engine)


@pytest.fixture
def world() -> Iterator[tuple[FastAPI, sessionmaker[Session]]]:
    """Production's shape: writes off by setting, which is how it ships."""
    yield from _world()


@pytest.fixture
def writing() -> Iterator[tuple[FastAPI, sessionmaker[Session]]]:
    """A deployment where writes are enabled, so the kill switch is the only
    thing that can stop them.

    Needed because the setting takes precedence in the words, and rightly: when
    writes are off by setting, reporting a stop instead would send somebody to
    release a switch that was never the reason. So the stop path can only be
    exercised with the setting on.
    """
    yield from _world(ads_writes_enabled=True)


def person(session: Session, email: str) -> UserAccount:
    account = UserAccount(google_sub=f"google-{email}", email=email)
    session.add(account)
    session.flush()
    return account


def signed_in(factory: sessionmaker[Session], email: str, level: Level | None = None) -> str:
    with factory() as session:
        account = person(session, email)
        if level is not None:
            grant(
                session,
                account_id=account.id,
                level=level,
                by_account_id=None,
                because=f"fixture at {level.value}",
            )
        token = sign_in_existing(session, account)
        session.commit()
        return token


def head(token: str) -> dict[str, str]:
    return {"x-session-token": token}


# --- nobody gets in by accident ---------------------------------------------


def test_every_route_refuses_somebody_signed_out(
    world: tuple[FastAPI, sessionmaker[Session]],
) -> None:
    app, _ = world
    with TestClient(app) as client:
        for method, path in EVERY_ROUTE:
            said = client.request(method, path, json={})
            assert said.status_code == 401, f"{method} {path} let a stranger in"


def test_every_route_refuses_a_signed_in_person_who_is_not_staff(
    world: tuple[FastAPI, sessionmaker[Session]],
) -> None:
    app, factory = world
    token = signed_in(factory, "customer@alpha.ie")
    with TestClient(app) as client:
        for method, path in EVERY_ROUTE:
            said = client.request(method, path, headers=head(token), json={})
            assert said.status_code == 403, f"{method} {path} let a customer in"


def test_a_merchants_own_admin_gets_nothing_through_the_http_layer(
    world: tuple[FastAPI, sessionmaker[Session]],
) -> None:
    """The guard being right does not prove the endpoint calls it.

    This person is `Role.ADMIN` of their own business. Wiring these routes to
    that role would hand every merchant's admin a window into every other
    merchant's business.
    """
    app, factory = world
    with factory() as session:
        owner = person(session, "owner@alpha.ie")
        place = home_for(session, owner)
        theirs = person(session, "admin@alpha.ie")
        token = invite(session, place, by=owner, email="admin@alpha.ie", role=Role.ADMIN)
        accept(session, token, theirs)
        their_token = sign_in_existing(session, theirs)
        session.commit()

    with TestClient(app) as client:
        for method, path in EVERY_ROUTE:
            said = client.request(method, path, headers=head(their_token), json={})
            assert said.status_code == 403, f"{method} {path} let a merchant's admin in"


def test_the_refusal_does_not_say_whether_the_panel_exists(
    world: tuple[FastAPI, sessionmaker[Session]],
) -> None:
    """403 for both a stranger and for staff at too low a level. A 404 would
    leak whether the panel exists; a 401 would invite a sign-in that cannot
    help."""
    app, factory = world
    outsider = signed_in(factory, "customer@alpha.ie")
    helper = signed_in(factory, "help@ppcway.com", Level.SUPPORT)
    with TestClient(app) as client:
        one = client.get("/v1/admin/platform", headers=head(outsider))
        two = client.get("/v1/admin/platform", headers=head(helper))
    assert one.status_code == two.status_code == 403


# --- whoami answers no without shouting -------------------------------------


def test_whoami_says_no_with_a_200_rather_than_a_403(
    world: tuple[FastAPI, sessionmaker[Session]],
) -> None:
    """The screen asks this first, and a console error on every page load for
    everybody who is not staff is noise."""
    app, factory = world
    token = signed_in(factory, "customer@alpha.ie")
    with TestClient(app) as client:
        said = client.get("/v1/admin/whoami", headers=head(token))
    assert said.status_code == 200
    assert said.json() == {"staff": False, "level": "", "may": [], "levels": []}


def test_whoami_describes_what_this_person_may_do(
    world: tuple[FastAPI, sessionmaker[Session]],
) -> None:
    app, factory = world
    token = signed_in(factory, "eng@ppcway.com", Level.ENGINEER)
    with TestClient(app) as client:
        body = client.get("/v1/admin/whoami", headers=head(token)).json()
    assert body["staff"] is True
    assert body["level"] == "engineer"
    assert "read_platform" in body["may"]
    assert "stop_writes" not in body["may"]
    assert {one["level"] for one in body["levels"]} == {"support", "engineer", "principal"}


# --- the level decides which routes answer ----------------------------------


def test_support_reads_a_merchant_but_not_the_platform(
    world: tuple[FastAPI, sessionmaker[Session]],
) -> None:
    app, factory = world
    token = signed_in(factory, "help@ppcway.com", Level.SUPPORT)
    with TestClient(app) as client:
        assert client.get("/v1/admin/merchants", headers=head(token)).status_code == 200
        assert client.get("/v1/admin/platform", headers=head(token)).status_code == 403
        assert client.get("/v1/admin/overview", headers=head(token)).status_code == 403


def test_an_engineer_reads_the_platform_but_cannot_stop_it(
    world: tuple[FastAPI, sessionmaker[Session]],
) -> None:
    app, factory = world
    token = signed_in(factory, "eng@ppcway.com", Level.ENGINEER)
    with TestClient(app) as client:
        assert client.get("/v1/admin/platform", headers=head(token)).status_code == 200
        said = client.post(
            "/v1/admin/platform/stop",
            headers=head(token),
            json={"because": "a perfectly good reason"},
        )
    assert said.status_code == 403


def test_only_a_principal_can_stop_and_release(
    writing: tuple[FastAPI, sessionmaker[Session]],
) -> None:
    app, factory = writing
    token = signed_in(factory, "boss@ppcway.com", Level.PRINCIPAL)
    with TestClient(app) as client:
        stopped = client.post(
            "/v1/admin/platform/stop",
            headers=head(token),
            json={"because": "the rules proposed nonsense overnight"},
        )
        assert stopped.status_code == 200, stopped.text
        assert stopped.json()["stopped"] is True

        where = client.get("/v1/admin/platform", headers=head(token)).json()
        assert where["anything_can_be_written"] is False
        assert "nonsense overnight" in where["words"]

        lifted = client.post("/v1/admin/platform/release", headers=head(token), json={})
        assert lifted.json()["released"] is True


def test_a_stop_with_no_real_reason_is_refused_with_a_422(
    world: tuple[FastAPI, sessionmaker[Session]],
) -> None:
    app, factory = world
    token = signed_in(factory, "boss@ppcway.com", Level.PRINCIPAL)
    with TestClient(app) as client:
        said = client.post("/v1/admin/platform/stop", headers=head(token), json={"because": "x"})
    assert said.status_code == 422
    assert "say why" in said.json()["detail"]


def test_releasing_nothing_says_so_rather_than_failing(
    world: tuple[FastAPI, sessionmaker[Session]],
) -> None:
    app, factory = world
    token = signed_in(factory, "boss@ppcway.com", Level.PRINCIPAL)
    with TestClient(app) as client:
        said = client.post("/v1/admin/platform/release", headers=head(token), json={})
    assert said.status_code == 200
    assert said.json() == {"released": False, "words": "Nothing was stopped."}


# --- the platform view -------------------------------------------------------


def test_the_overview_carries_figures_as_sentences(
    world: tuple[FastAPI, sessionmaker[Session]],
) -> None:
    app, factory = world
    token = signed_in(factory, "eng@ppcway.com", Level.ENGINEER)
    with TestClient(app) as client:
        body = client.get("/v1/admin/overview", headers=head(token)).json()
    assert body["window"] == "7d"
    assert body["healthy"] is True
    assert body["figures"]["merchants"]["words"] == "0 businesses."
    assert body["figures"]["proposed"]["window"] == "7d"


def test_the_overview_honours_the_window_asked_for(
    world: tuple[FastAPI, sessionmaker[Session]],
) -> None:
    app, factory = world
    token = signed_in(factory, "eng@ppcway.com", Level.ENGINEER)
    with TestClient(app) as client:
        assert (
            client.get("/v1/admin/overview?window=30d", headers=head(token)).json()["window"]
            == "30d"
        )
        # A window somebody typed must not take the panel down.
        assert (
            client.get("/v1/admin/overview?window=forever", headers=head(token)).json()["window"]
            == "7d"
        )


def test_no_flag_is_offered_as_changeable(
    world: tuple[FastAPI, sessionmaker[Session]],
) -> None:
    """A toggle for something only a deploy can change teaches people the panel
    is lying to them."""
    app, factory = world
    token = signed_in(factory, "eng@ppcway.com", Level.ENGINEER)
    with TestClient(app) as client:
        body = client.get("/v1/admin/platform", headers=head(token)).json()
    assert body["flags"], "there is something to show"
    assert all(not one["changeable"] for one in body["flags"])
    assert all(one["why_not"] for one in body["flags"])
    names = {one["name"]: one for one in body["flags"]}
    assert names["Writing to Google Ads"]["on"] is False


def test_the_screen_is_told_whether_to_show_the_stop_button(
    world: tuple[FastAPI, sessionmaker[Session]],
) -> None:
    app, factory = world
    boss = signed_in(factory, "boss@ppcway.com", Level.PRINCIPAL)
    engineer = signed_in(factory, "eng@ppcway.com", Level.ENGINEER)
    with TestClient(app) as client:
        assert client.get("/v1/admin/platform", headers=head(boss)).json()["may_stop_writes"]
        assert not client.get("/v1/admin/platform", headers=head(engineer)).json()[
            "may_stop_writes"
        ]


# --- opening a business is written down -------------------------------------


def test_opening_one_merchant_leaves_a_record(
    world: tuple[FastAPI, sessionmaker[Session]],
) -> None:
    """The route the record exists for. `note_look` is called by the endpoint
    rather than the view underneath, because a record written where it is
    convenient goes missing when somebody adds a second caller."""
    app, factory = world
    token = signed_in(factory, "help@ppcway.com", Level.SUPPORT)
    with factory() as session:
        owner = person(session, "owner@alpha.ie")
        place = home_for(session, owner)
        place.name = "Alpha Plumbing"
        session.commit()
        place_id = place.id

    with TestClient(app) as client:
        said = client.get(f"/v1/admin/merchants/{place_id}", headers=head(token))
    assert said.status_code == 200
    assert said.json()["name"] == "Alpha Plumbing"

    with factory() as session:
        looks = list(session.scalars(sa.select(StaffLook)))
    opened = [one for one in looks if one.looked_at == "merchant"]
    assert len(opened) == 1
    assert opened[0].organization_name == "Alpha Plumbing"
    assert opened[0].level == "support"


def test_browsing_the_list_is_recorded_too(
    world: tuple[FastAPI, sessionmaker[Session]],
) -> None:
    """ "Who went looking through the customer list" is worth being able to
    answer as well."""
    app, factory = world
    token = signed_in(factory, "help@ppcway.com", Level.SUPPORT)
    with TestClient(app) as client:
        client.get("/v1/admin/merchants", headers=head(token))
    with factory() as session:
        looks = list(session.scalars(sa.select(StaffLook)))
    assert [one.looked_at for one in looks] == ["list"]
    assert looks[0].organization_id is None


def test_a_business_that_does_not_exist_is_a_404_not_a_blank_page(
    world: tuple[FastAPI, sessionmaker[Session]],
) -> None:
    app, factory = world
    token = signed_in(factory, "help@ppcway.com", Level.SUPPORT)
    with TestClient(app) as client:
        said = client.get(f"/v1/admin/merchants/{uuid.uuid4()}", headers=head(token))
    assert said.status_code == 404


def test_a_merchant_can_be_told_who_looked_at_them(
    world: tuple[FastAPI, sessionmaker[Session]],
) -> None:
    app, factory = world
    token = signed_in(factory, "help@ppcway.com", Level.SUPPORT)
    with factory() as session:
        owner = person(session, "owner@alpha.ie")
        place = home_for(session, owner)
        session.commit()
        place_id = place.id
    with TestClient(app) as client:
        client.get(f"/v1/admin/merchants/{place_id}", headers=head(token))
        body = client.get(f"/v1/admin/merchants/{place_id}/who-looked", headers=head(token)).json()
    assert len(body["looks"]) == 1
    assert body["looks"][0]["level"] == "support"
    # A person, not only an id: the list exists to be read back by somebody.
    assert body["looks"][0]["who"] == "help@ppcway.com"


def test_the_overview_carries_the_series_its_chart_is_drawn_from(
    world: tuple[FastAPI, sessionmaker[Session]],
) -> None:
    app, factory = world
    token = signed_in(factory, "eng@ppcway.com", Level.ENGINEER)
    with TestClient(app) as client:
        body = client.get("/v1/admin/overview?window=30d", headers=head(token)).json()
    assert body["series"]["step"] == "day"
    assert len(body["series"]["points"]) == 30
    # An empty platform is a run of empty days, not a missing chart.
    assert body["series"]["points"][0]["counts"] == {}


def test_the_access_history_names_people_rather_than_ids(
    world: tuple[FastAPI, sessionmaker[Session]],
) -> None:
    app, factory = world
    boss = signed_in(factory, "boss@ppcway.com", Level.PRINCIPAL)
    with factory() as session:
        person(session, "newbie@ppcway.com")
        session.commit()
    with TestClient(app) as client:
        made = client.post(
            "/v1/admin/staff",
            headers=head(boss),
            json={"email": "newbie@ppcway.com", "level": "support", "because": "joins on Monday"},
        )
        assert made.status_code == 200, made.text
        grants = client.get("/v1/admin/staff", headers=head(boss)).json()["grants"]
    assert (grants[0]["who"], grants[0]["by"]) == ("newbie@ppcway.com", "boss@ppcway.com")
    # The fixture's grant had nobody behind it, the way the command line makes
    # the first principal, and says so with an empty name rather than a guess.
    assert (grants[-1]["who"], grants[-1]["by"]) == ("boss@ppcway.com", "")


# --- granting access ---------------------------------------------------------


def test_a_principal_can_grant_and_withdraw_by_email(
    world: tuple[FastAPI, sessionmaker[Session]],
) -> None:
    """By email because the person doing it is reading a name off a message."""
    app, factory = world
    boss = signed_in(factory, "boss@ppcway.com", Level.PRINCIPAL)
    with factory() as session:
        person(session, "newbie@ppcway.com")
        session.commit()

    with TestClient(app) as client:
        made = client.post(
            "/v1/admin/staff",
            headers=head(boss),
            json={"email": "newbie@ppcway.com", "level": "support", "because": "joins on Monday"},
        )
        assert made.status_code == 200, made.text
        assert made.json()["level"] == "support"

        gone = client.post(
            "/v1/admin/staff",
            headers=head(boss),
            json={"email": "newbie@ppcway.com", "level": "", "because": "left the company"},
        )
        assert gone.json()["level"] == ""


def test_nobody_can_change_their_own_access(
    world: tuple[FastAPI, sessionmaker[Session]],
) -> None:
    """So no single person can quietly promote themselves."""
    app, factory = world
    boss = signed_in(factory, "boss@ppcway.com", Level.PRINCIPAL)
    with TestClient(app) as client:
        said = client.post(
            "/v1/admin/staff",
            headers=head(boss),
            json={"email": "boss@ppcway.com", "level": "principal", "because": "me"},
        )
    assert said.status_code == 422
    assert "your own access" in said.json()["detail"]


def test_granting_to_somebody_who_never_signed_in_explains_itself(
    world: tuple[FastAPI, sessionmaker[Session]],
) -> None:
    app, factory = world
    boss = signed_in(factory, "boss@ppcway.com", Level.PRINCIPAL)
    with TestClient(app) as client:
        said = client.post(
            "/v1/admin/staff",
            headers=head(boss),
            json={"email": "ghost@ppcway.com", "level": "support", "because": "a good reason"},
        )
    assert said.status_code == 404
    assert "sign in once" in said.json()["detail"]


def test_a_grant_with_no_reason_is_refused(
    world: tuple[FastAPI, sessionmaker[Session]],
) -> None:
    app, factory = world
    boss = signed_in(factory, "boss@ppcway.com", Level.PRINCIPAL)
    with factory() as session:
        person(session, "newbie@ppcway.com")
        session.commit()
    with TestClient(app) as client:
        said = client.post(
            "/v1/admin/staff",
            headers=head(boss),
            json={"email": "newbie@ppcway.com", "level": "support", "because": ""},
        )
    assert said.status_code == 422
    assert "stated reason" in said.json()["detail"]


def test_an_unknown_level_is_refused_with_the_choices(
    world: tuple[FastAPI, sessionmaker[Session]],
) -> None:
    app, factory = world
    boss = signed_in(factory, "boss@ppcway.com", Level.PRINCIPAL)
    with factory() as session:
        person(session, "newbie@ppcway.com")
        session.commit()
    with TestClient(app) as client:
        said = client.post(
            "/v1/admin/staff",
            headers=head(boss),
            json={"email": "newbie@ppcway.com", "level": "superadmin", "because": "a reason"},
        )
    assert said.status_code == 422
    assert "principal" in said.json()["detail"]


def test_the_grant_history_is_returned_not_just_the_current_state(
    world: tuple[FastAPI, sessionmaker[Session]],
) -> None:
    """ "Who could see this in March" is the question these tables exist for."""
    app, factory = world
    boss = signed_in(factory, "boss@ppcway.com", Level.PRINCIPAL)
    with factory() as session:
        person(session, "newbie@ppcway.com")
        session.commit()
    with TestClient(app) as client:
        client.post(
            "/v1/admin/staff",
            headers=head(boss),
            json={"email": "newbie@ppcway.com", "level": "support", "because": "joins Monday"},
        )
        client.post(
            "/v1/admin/staff",
            headers=head(boss),
            json={"email": "newbie@ppcway.com", "level": "", "because": "left"},
        )
        body = client.get("/v1/admin/staff", headers=head(boss)).json()
    theirs = [one for one in body["grants"] if one["because"] in ("joins Monday", "left")]
    assert len(theirs) == 2, "the grant is still in the history after withdrawal"
    assert {one["granted"] for one in theirs} == {True, False}


def test_quota_needs_an_account_named(world: tuple[FastAPI, sessionmaker[Session]]) -> None:
    app, factory = world
    token = signed_in(factory, "eng@ppcway.com", Level.ENGINEER)
    with TestClient(app) as client:
        assert client.get("/v1/admin/quota", headers=head(token)).status_code == 422
        said = client.get("/v1/admin/quota?customer_id=2580586343", headers=head(token))
    assert said.status_code == 200
    assert said.json()["used"] == 0


def test_the_setting_is_reported_ahead_of_a_stop_when_both_are_true(
    world: tuple[FastAPI, sessionmaker[Session]],
) -> None:
    """Which cause gets the sentence, when writes are off by setting *and*
    stopped by a switch.

    The setting wins, and that is the useful answer: releasing the switch would
    change nothing, so pointing somebody at it would waste their time during an
    incident. The stop is still listed under `stops` for whoever needs it.
    """
    app, factory = world
    token = signed_in(factory, "boss@ppcway.com", Level.PRINCIPAL)
    with TestClient(app) as client:
        client.post(
            "/v1/admin/platform/stop",
            headers=head(token),
            json={"because": "stopped during an incident"},
        )
        body = client.get("/v1/admin/platform", headers=head(token)).json()
    assert "takes a deploy to change" in body["words"]
    assert body["anything_can_be_written"] is False
    assert [one["because"] for one in body["stops"]] == ["stopped during an incident"]


def test_jobs_and_errors_need_engineer_access(
    world: tuple[FastAPI, sessionmaker[Session]],
) -> None:
    """Somebody answering a support ticket has no business in the error stream."""
    app, factory = world
    helper = signed_in(factory, "help@ppcway.com", Level.SUPPORT)
    engineer = signed_in(factory, "eng@ppcway.com", Level.ENGINEER)
    with TestClient(app) as client:
        assert client.get("/v1/admin/jobs", headers=head(helper)).status_code == 403
        assert client.get("/v1/admin/errors", headers=head(helper)).status_code == 403
        assert client.get("/v1/admin/jobs", headers=head(engineer)).status_code == 200
        assert client.get("/v1/admin/errors", headers=head(engineer)).status_code == 200


def test_the_jobs_route_answers_with_an_empty_list_not_an_error(
    world: tuple[FastAPI, sessionmaker[Session]],
) -> None:
    """A fresh deployment has run nothing. That is not a fault."""
    app, factory = world
    token = signed_in(factory, "eng@ppcway.com", Level.ENGINEER)
    with TestClient(app) as client:
        assert client.get("/v1/admin/jobs", headers=head(token)).json() == {"runs": []}
        assert client.get("/v1/admin/errors", headers=head(token)).json()["faults"] == []
