"""The campaign builder through the endpoints a merchant's browser uses.

Keyword Planner, the model and Google's write side are faked at their edges;
everything between -- who may build, who may launch, what is checked, what is
kept -- is the real code.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
import sqlalchemy as sa
from cryptography.fernet import Fernet
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.orm import Session, sessionmaker

from ppcway.ads import models as ads_models
from ppcway.ads.planner import Demand, Search
from ppcway.api.app import create_app
from ppcway.auth import google
from ppcway.auth.models import UserAccount
from ppcway.builder.draft import Written
from ppcway.builder.models import CampaignDraft
from ppcway.builder.site import Site, own_name_or_not
from ppcway.builder.validate import Business
from ppcway.chat import transcript as _transcript  # noqa: F401 - registers its table
from ppcway.config import Settings
from ppcway.db.base import Base
from ppcway.db.session import get_session
from ppcway.gateway import switch
from ppcway.gateway.port import Created, Together
from ppcway.model import log as _prompt_log  # noqa: F401 - registers its table
from ppcway.opt import consent as _consent  # noqa: F401 - registers its table
from ppcway.org.places import home_for
from ppcway.staff import models as _staff  # noqa: F401 - registers its table

KEY = Fernet.generate_key()
CUSTOMER = "2580586343"

BRIEF: dict[str, Any] = {
    "name": "PDF tools",
    "themes": ["pdf to word", "compress pdf"],
    "final_url": "https://pdfezy.com/",
    "daily_budget": 20,
    "places": [{"resource": "geoTargetConstants/2616", "name": "Poland", "kind": "Country"}],
    "language": {"resource": "languageConstants/1000", "name": "English"},
    "bidding": "clicks",
    "negatives": ["jobs"],
    "claims": {"free_quotes": False},
}


class Google:
    """Google's write side, faked -- and, for the tests' convenience, what the
    landing page is called and who the ad text was written for."""

    def __init__(self) -> None:
        self.sent: list[Together] = []
        self.site = Site()
        self.wrote_for: list[Business] = []

    def mutate_together(self, together: Together) -> Created:
        self.sent.append(together)
        if together.validate_only:
            return Created(names=(), checked_only=True)
        return Created(
            names=tuple(
                f"customers/{CUSTOMER}/campaigns/777"
                if op.resource_type == "campaign"
                else f"customers/{CUSTOMER}/x/{n}"
                for n, op in enumerate(together.operations)
            )
        )


@pytest.fixture
def world(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[FastAPI, sessionmaker[Session], Google]]:
    engine = sa.create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=sa.pool.StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)

    monkeypatch.setattr(
        google.id_token,  # type: ignore[attr-defined]
        "verify_oauth2_token",
        lambda credential, *a, **k: {
            "sub": f"google-{credential[:6]}",
            "email": f"{credential[:6]}@pdfezy.com",
            "email_verified": True,
            "name": credential[:6],
        },
    )
    from ppcway.ads import planner
    from ppcway.builder import build, site
    from ppcway.gateway import send

    door = Google()

    def ideas(seeds: list[str], **_: Any) -> Demand:
        theme = seeds[0]
        return Demand(
            read=True,
            searches=[
                Search(theme, 9000, "LOW", 0.4, 1.2),
                Search(f"{theme} online", 3000, "LOW", 0.4, 1.2),
                Search("ilovepdf", 90000, "LOW", 0.4, 1.2),
            ],
        )

    monkeypatch.setattr(planner, "ideas_for", ideas)
    monkeypatch.setattr(
        planner,
        "places_called",
        lambda name, **_: [
            {"resource": "geoTargetConstants/2616", "name": "Poland", "kind": "Country"}
        ],
    )

    def written(models: Any, **k: Any) -> Written:
        door.wrote_for.append(k["business"])
        return Written(
            headlines=tuple(f"Convert files fast {n}" for n in range(11)),
            descriptions=("Turn a PDF into a Word file.", "Works in your browser."),
            asked=1,
        )

    monkeypatch.setattr(build, "write_copy", written)
    # The landing page is never fetched in a test. Each test that cares says
    # what the page is called; the rest get a page that could not be read.
    monkeypatch.setattr(site, "read_site", lambda url, **k: door.site)
    monkeypatch.setattr("ppcway.api.app.fresh_access_token", lambda *a, **k: "access")
    monkeypatch.setattr("ppcway.api.app._sync", lambda *a, **k: None)
    monkeypatch.setattr(send, "doors", lambda settings: lambda connection: door)

    app = create_app(
        Settings(
            google_signin_client_id="test-client",
            google_oauth_client_id="test-client",
            google_oauth_client_secret=SecretStr("test-secret"),
            google_ads_developer_token=SecretStr("test-token"),
            google_oauth_token_key=SecretStr(KEY.decode()),
        )
    )

    def one_session() -> Iterator[Session]:
        session = factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_session] = one_session
    yield app, factory, door
    Base.metadata.drop_all(engine)


def owner(client: TestClient, factory: sessionmaker[Session], who: str = "ownerx") -> str:
    token = client.post("/v1/auth/google", json={"credential": who + "d" * 40}).json()["token"]
    with factory() as session:
        person = session.scalars(
            sa.select(UserAccount).where(UserAccount.email == f"{who[:6]}@pdfezy.com")
        ).one()
        session.add(
            ads_models.AdsConnection(
                account_id=person.id,
                organization_id=home_for(session, person).id,
                ciphertext=Fernet(KEY).encrypt(b"a-permission").decode(),
                customer_id=CUSTOMER,
                customer_name="PDFezy",
                currency="USD",
                account_status="ENABLED",
                status_read_at=datetime.now(UTC) - timedelta(hours=1),
            )
        )
        session.commit()
    return str(token)


def head(token: str) -> dict[str, str]:
    return {"x-session-token": token}


def test_a_campaign_is_written_from_real_searches_and_nothing_reaches_google(
    world: tuple[FastAPI, sessionmaker[Session], Google],
) -> None:
    app, factory, door = world
    with TestClient(app) as client:
        token = owner(client, factory)
        made = client.post("/v1/campaigns/drafts", headers=head(token), json=BRIEF)
    assert made.status_code == 201, made.text
    draft = made.json()
    themes = draft["plan"]["themes"]
    assert [t["name"] for t in themes] == ["pdf to word", "compress pdf"]
    assert [k["text"] for k in themes[0]["keywords"]] == ["pdf to word", "pdf to word online"]
    assert len(themes[0]["headlines"]) == 11
    assert draft["sentence"].startswith("We'll show your ads to people in Poland")
    assert any("political advertising" in one for one in draft["missing"]), (
        "the merchant has to confirm it, nobody assumes it for them"
    )
    assert door.sent == []


@pytest.mark.parametrize(
    ("change", "says"),
    [
        ({"themes": []}, "at least one service"),
        ({"places": []}, "at least one place"),
        ({"final_url": "pdfezy.com"}, "https://"),
        ({"daily_budget": 0}, "above zero"),
        ({"language": {}}, "language"),
    ],
)
def test_a_brief_that_cannot_be_built_says_what_is_missing(
    world: tuple[FastAPI, sessionmaker[Session], Google], change: dict[str, Any], says: str
) -> None:
    app, factory, _door = world
    with TestClient(app) as client:
        token = owner(client, factory)
        refused = client.post("/v1/campaigns/drafts", headers=head(token), json={**BRIEF, **change})
    assert refused.status_code == 422
    assert says in refused.json()["detail"]


def test_edits_are_checked_and_keywords_can_only_be_taken_out(
    world: tuple[FastAPI, sessionmaker[Session], Google],
) -> None:
    app, factory, _door = world
    with TestClient(app) as client:
        token = owner(client, factory)
        draft = client.post("/v1/campaigns/drafts", headers=head(token), json=BRIEF).json()
        edited = client.post(
            f"/v1/campaigns/drafts/{draft['id']}",
            headers=head(token),
            json={
                "not_political": True,
                "daily_budget": 25,
                "themes": [
                    {
                        "keywords": ["pdf to word", "something i typed"],
                        "headlines": [*[f"Word files in seconds {n}" for n in range(9)], "BEST!!!"],
                    }
                ],
            },
        ).json()
    theme = edited["plan"]["themes"][0]
    assert [k["text"] for k in theme["keywords"]] == ["pdf to word"], (
        "taken out, yes; typed in, no -- only Keyword Planner adds a keyword"
    )
    assert "BEST!!!" not in theme["headlines"]
    assert [r["text"] for r in edited["refused"]] == ["BEST!!!"]
    assert edited["plan"]["daily_budget"] == 25.0
    assert edited["missing"] == []


def test_launching_creates_the_campaign_through_the_one_door(
    world: tuple[FastAPI, sessionmaker[Session], Google],
) -> None:
    app, factory, door = world
    with TestClient(app) as client:
        token = owner(client, factory)
        draft = client.post("/v1/campaigns/drafts", headers=head(token), json=BRIEF).json()
        client.post(
            f"/v1/campaigns/drafts/{draft['id']}", headers=head(token), json={"not_political": True}
        )
        with factory() as session:
            switch.set_gate(session, is_open=True, because="testing the builder", set_by=None)
        said = client.post(f"/v1/campaigns/drafts/{draft['id']}/launch", headers=head(token)).json()
    assert said["live"] is True, said
    assert said["campaign"] == f"customers/{CUSTOMER}/campaigns/777"
    assert said["status"] == "launched"
    assert [t.validate_only for t in door.sent] == [True, False]
    with factory() as session:
        row = session.scalars(sa.select(CampaignDraft)).one()
        assert row.launched_by is not None


def test_with_writes_off_a_launch_creates_nothing_and_says_so(
    world: tuple[FastAPI, sessionmaker[Session], Google],
) -> None:
    app, factory, door = world
    with TestClient(app) as client:
        token = owner(client, factory)
        draft = client.post("/v1/campaigns/drafts", headers=head(token), json=BRIEF).json()
        client.post(
            f"/v1/campaigns/drafts/{draft['id']}", headers=head(token), json={"not_political": True}
        )
        said = client.post(f"/v1/campaigns/drafts/{draft['id']}/launch", headers=head(token)).json()
    assert said["live"] is False
    assert "not writing to Google Ads" in said["words"]
    assert door.sent == []


def test_another_business_cannot_see_or_launch_the_draft(
    world: tuple[FastAPI, sessionmaker[Session], Google],
) -> None:
    app, factory, door = world
    with TestClient(app) as client:
        token = owner(client, factory, who="owner1")
        draft = client.post("/v1/campaigns/drafts", headers=head(token), json=BRIEF).json()
        stranger = owner(client, factory, who="other2")
        assert (
            client.get(f"/v1/campaigns/drafts/{draft['id']}", headers=head(stranger)).status_code
            == 404
        )
        refused = client.post(f"/v1/campaigns/drafts/{draft['id']}/launch", headers=head(stranger))
    assert refused.status_code == 404
    assert door.sent == []


def test_the_place_picker_answers_with_google_s_own_names(
    world: tuple[FastAPI, sessionmaker[Session], Google],
) -> None:
    app, factory, _door = world
    with TestClient(app) as client:
        token = owner(client, factory)
        found = client.get("/v1/campaigns/places?q=pola", headers=head(token)).json()
        nothing = client.get("/v1/campaigns/places?q=p", headers=head(token)).json()
    assert found["places"][0]["resource"] == "geoTargetConstants/2616"
    assert nothing["places"] == [], "one letter is not a search"


def test_signed_out_gets_nothing(world: tuple[FastAPI, sessionmaker[Session], Google]) -> None:
    app, _factory, _door = world
    with TestClient(app) as client:
        assert client.post("/v1/campaigns/drafts", json=BRIEF).status_code == 401
        assert client.get("/v1/campaigns/places?q=pol").status_code == 401


def test_the_ads_are_written_for_the_website_not_the_person_signed_in(
    world: tuple[FastAPI, sessionmaker[Session], Google],
) -> None:
    """9 November: the owner's ads were drafted for "Abdul Razzaq", the person,
    because PPCWay names a business after whoever signed in first. The page the
    ads send people to says whose ads they are."""
    app, factory, door = world
    door.site = Site(name="PDFezy", title="PDFezy | Free PDF tools online")
    with TestClient(app) as client:
        token = owner(client, factory)
        made = client.post("/v1/campaigns/drafts", headers=head(token), json=BRIEF)
    assert made.status_code == 201, made.text
    business = made.json()["plan"]["business"]
    assert business["name"] == "PDFezy"
    assert business["site_title"] == "PDFezy | Free PDF tools online"
    assert door.wrote_for and all(one.name == "PDFezy" for one in door.wrote_for)
    assert "ownerx" not in [w.lower() for w in business["brand_words"]], (
        "the person's own name is not a brand an ad may carry"
    )


def test_without_a_readable_page_the_google_ads_account_name_is_used(
    world: tuple[FastAPI, sessionmaker[Session], Google],
) -> None:
    app, factory, _door = world
    with TestClient(app) as client:
        token = owner(client, factory)
        made = client.post("/v1/campaigns/drafts", headers=head(token), json=BRIEF)
    business = made.json()["plan"]["business"]
    assert business["name"] == "PDFezy", "the account's name, never the person's"
    assert business["site_title"] == ""


def test_a_business_named_after_a_person_is_not_a_business_name() -> None:
    people = [("Abdul Razzaq", "abdulrazzaq0621@gmail.com")]
    assert own_name_or_not("Abdul Razzaq", people) == ""
    assert own_name_or_not("abdulrazzaq0621", people) == ""
    assert own_name_or_not("  PDFezy  ", people) == "PDFezy"
    assert own_name_or_not("", people) == ""


def test_an_unreadable_page_reads_as_nothing() -> None:
    from ppcway.builder.site import read_site

    def refused(*a: Any, **k: Any) -> Any:
        raise RuntimeError("private address")

    assert read_site("https://10.0.0.1/", crawl=refused) == Site()


def test_a_long_title_is_cut_before_it_reaches_a_prompt() -> None:
    from types import SimpleNamespace

    from ppcway.builder.site import MOST_TITLE, read_site

    page = SimpleNamespace(business_name="PDFezy", meta_title="word " * 80)
    said = read_site("https://pdfezy.com/", crawl=lambda *a, **k: page)
    assert said.name == "PDFezy"
    assert len(said.title) <= MOST_TITLE
