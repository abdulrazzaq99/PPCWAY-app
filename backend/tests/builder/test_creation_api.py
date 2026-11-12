"""Creating a campaign on Google's own steps, through the endpoints the browser uses.

Google's write side, Keyword Planner, the model and the account reads are
faked at their edges (the fixture is the first builder's); what each step
saves, what is checked, and what reaches Google are the real code.
"""

# The `world` fixture is the first builder's, imported by name: pytest finds it
# that way, and ruff reads each test's use of it as a redefinition.
# ruff: noqa: F811

from __future__ import annotations

import base64
import struct
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from ppcway.gateway import switch
from ppcway.gateway.port import Created, GoogleRefused, Together

from .test_builder_api import CUSTOMER, Google, head, owner, world  # noqa: F401

GOALS = {
    "goals": [
        {
            "category": "SUBMIT_LEAD_FORM",
            "origin": "WEBSITE",
            "biddable": True,
            "label": "Submit lead forms",
            "actions": [{"name": "Contact form", "status": "ENABLED", "primary": True}],
        }
    ],
    "tracking": True,
    "reason": "",
}

STEP_ONE = {
    "objective": "leads",
    "type": "SEARCH",
    "name": "PDF tools",
    "goals": {
        "account_default": True,
        "available": [{"category": "SUBMIT_LEAD_FORM", "origin": "WEBSITE"}],
    },
    "ways": {"website": True, "website_url": "https://pdfezy.com"},
}


@pytest.fixture(autouse=True)
def account_reads(monkeypatch: pytest.MonkeyPatch) -> None:
    from ppcway.ads import setup

    monkeypatch.setattr(setup, "conversion_goals", lambda customer_id, **k: GOALS)
    monkeypatch.setattr(
        setup, "image_url", lambda customer_id, asset, **k: {"url": "https://lh3/x.png"}
    )
    monkeypatch.setattr(
        setup, "billing_ready", lambda customer_id, **k: {"known": True, "ready": True}
    )


def _png(width: int, height: int) -> str:
    raw = b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", width, height)
    return base64.b64encode(raw + b"\x08\x02\x00\x00\x00" + b"\x00" * 64).decode()


def _writes_on(factory: sessionmaker[Session]) -> None:
    with factory() as session:
        switch.set_gate(session, is_open=True, because="testing creation", set_by=None)
        session.commit()


def _complete(client: TestClient, token: str, draft: str) -> dict[str, Any]:
    saved = client.post(
        f"/v1/campaigns/v2/{draft}",
        headers=head(token),
        json={
            "eu_political": False,
            "locations": {
                "mode": "custom",
                "targets": [{"resource": "geoTargetConstants/2124", "name": "Canada"}],
            },
            "budget": {"type": "daily", "amount": 25},
            "ad_groups": [
                {
                    "name": "PDF to Word",
                    "keywords": [{"text": "pdf to word", "match": "PHRASE"}],
                    "ads": [
                        {
                            "headlines": [
                                {"text": "Convert PDF to Word"},
                                {"text": "Fast PDF converter"},
                                {"text": "Try PDFezy today"},
                            ],
                            "descriptions": [
                                {"text": "Turn any PDF into a Word file in seconds."},
                                {"text": "Works in your browser, on any device."},
                            ],
                        }
                    ],
                }
            ],
        },
    )
    assert saved.status_code == 200, saved.text
    return saved.json()


def test_step_one_shows_googles_objectives_types_and_the_accounts_goals(
    world: tuple[FastAPI, sessionmaker[Session], Google],
) -> None:
    app, factory, _door = world
    with TestClient(app) as client:
        token = owner(client, factory)
        said = client.get("/v1/campaigns/setup", headers=head(token)).json()
    assert said["connected"] is True
    assert [o["label"] for o in said["objectives"].values()][:3] == [
        "Sales",
        "Leads",
        "Website traffic",
    ]
    assert (
        said["types"]["VIDEO"]["creatable"] is False
        and "Demand Gen" in said["types"]["VIDEO"]["why"]
    )
    assert said["types"]["SMART"]["creatable"] is False
    assert said["conversion"]["goals"][0]["label"] == "Submit lead forms"
    assert said["steps"]["SEARCH"] == [
        "bidding",
        "settings",
        "ai_max",
        "generation",
        "ads",
        "budget",
        "review",
    ]


def test_step_one_makes_a_draft_with_googles_defaults_and_sends_nothing(
    world: tuple[FastAPI, sessionmaker[Session], Google],
) -> None:
    app, factory, door = world
    with TestClient(app) as client:
        token = owner(client, factory)
        made = client.post("/v1/campaigns/v2", headers=head(token), json=STEP_ONE)
    assert made.status_code == 201, made.text
    draft = made.json()
    spec = draft["spec"]
    assert spec["ai_max"]["enabled"] is True
    assert spec["networks"] == {"search_partners": True, "display": True}
    assert spec["locations"]["target_option"] == "PRESENCE_OR_INTEREST"
    assert spec["bidding"]["focus"] == "conversions"
    assert [s["id"] for s in draft["steps"]][:3] == ["goal", "bidding", "settings"]
    assert any("EU political" in p["words"] for p in draft["problems"])
    assert door.sent == []


@pytest.mark.parametrize(
    ("kind", "says"),
    [("VIDEO", "Demand Gen"), ("SMART", "23 September 2026"), ("NOPE", "campaign type")],
)
def test_types_google_will_not_let_an_app_create_are_refused_with_why(
    world: tuple[FastAPI, sessionmaker[Session], Google], kind: str, says: str
) -> None:
    app, factory, _door = world
    with TestClient(app) as client:
        token = owner(client, factory)
        said = client.post("/v1/campaigns/v2", headers=head(token), json={**STEP_ONE, "type": kind})
    assert said.status_code == 422 and says in said.json()["detail"]


def test_each_step_saves_its_section_and_the_type_cannot_change(
    world: tuple[FastAPI, sessionmaker[Session], Google],
) -> None:
    app, factory, _door = world
    with TestClient(app) as client:
        token = owner(client, factory)
        draft = client.post("/v1/campaigns/v2", headers=head(token), json=STEP_ONE).json()["id"]
        saved = client.post(
            f"/v1/campaigns/v2/{draft}",
            headers=head(token),
            json={"type": "PERFORMANCE_MAX", "bidding": {"focus": "clicks", "max_cpc": 2}},
        )
        again = client.get(f"/v1/campaigns/v2/{draft}", headers=head(token)).json()
        bad = client.post(
            f"/v1/campaigns/v2/{draft}", headers=head(token), json={"bidding": {"focus": "nope"}}
        )
    assert saved.status_code == 200
    assert again["spec"]["type"] == "SEARCH"
    assert again["spec"]["bidding"]["max_cpc"] == 2
    assert bad.status_code == 422 and "bidding.focus" in bad.json()["detail"]


def test_generation_writes_ad_groups_from_real_searches(
    world: tuple[FastAPI, sessionmaker[Session], Google],
) -> None:
    app, factory, door = world
    with TestClient(app) as client:
        token = owner(client, factory)
        draft = client.post("/v1/campaigns/v2", headers=head(token), json=STEP_ONE).json()["id"]
        made = client.post(
            f"/v1/campaigns/v2/{draft}/generate",
            headers=head(token),
            json={
                "url": "https://pdfezy.com",
                "services": ["pdf to word", "compress pdf"],
                "summary": "Browser PDF tools for small offices.",
            },
        )
    assert made.status_code == 200, made.text
    assert door.wrote_for[0].summary == "Browser PDF tools for small offices.", "Otto reads it"
    groups = made.json()["spec"]["ad_groups"]
    assert [g["name"] for g in groups] == ["pdf to word", "compress pdf"]
    assert {k["match"] for k in groups[0]["keywords"]} == {"BROAD"}, "Google's default match"
    assert len(groups[0]["ads"][0]["headlines"]) == 11
    assert made.json()["spec"]["generation"]["done"] is True
    assert door.sent == []


def test_review_asks_google_to_check_the_whole_campaign_and_creates_nothing(
    world: tuple[FastAPI, sessionmaker[Session], Google],
) -> None:
    app, factory, door = world
    with TestClient(app) as client:
        token = owner(client, factory)
        draft = client.post("/v1/campaigns/v2", headers=head(token), json=STEP_ONE).json()["id"]
        early = client.post(f"/v1/campaigns/v2/{draft}/check", headers=head(token)).json()
        assert early["ok"] is False and door.sent == [], "PPCWay's own checks come first"
        _complete(client, token, draft)
        said = client.post(f"/v1/campaigns/v2/{draft}/check", headers=head(token)).json()
    assert said["ok"] is True, said
    assert len(door.sent) == 1 and door.sent[0].validate_only is True
    kinds = {op.resource_type for op in door.sent[0].operations}
    assert {"campaign_budget", "campaign", "campaign_criterion", "ad_group", "ad_group_ad"} <= kinds


def test_googles_errors_come_back_all_at_once_filed_by_step(
    world: tuple[FastAPI, sessionmaker[Session], Google],
) -> None:
    app, factory, door = world

    def refuse(together: Together) -> Created:
        refused = GoogleRefused("Google refused the campaign")
        refused.problems = [
            {
                "resource_type": "campaign_budget",
                "field": "amount_micros",
                "message": "Too low.",
                "code": "x",
                "about": "the budget",
            },
            {
                "resource_type": "ad_group_ad",
                "field": "ad.responsive_search_ad",
                "message": "Policy.",
                "code": "y",
                "about": "an ad",
            },
        ]
        raise refused

    door.mutate_together = refuse  # type: ignore[method-assign]
    with TestClient(app) as client:
        token = owner(client, factory)
        draft = client.post("/v1/campaigns/v2", headers=head(token), json=STEP_ONE).json()["id"]
        _complete(client, token, draft)
        said = client.post(f"/v1/campaigns/v2/{draft}/check", headers=head(token)).json()
    assert said["ok"] is False
    google = [p for p in said["problems"] if p["words"].startswith("Google:")]
    assert [(p["step"], p["words"]) for p in google] == [
        ("budget", "Google: Too low. (the budget)"),
        ("ads", "Google: Policy. (an ad)"),
    ]


def test_publishing_creates_it_whole_and_records_it(
    world: tuple[FastAPI, sessionmaker[Session], Google],
) -> None:
    app, factory, door = world
    with TestClient(app) as client:
        token = owner(client, factory)
        draft = client.post("/v1/campaigns/v2", headers=head(token), json=STEP_ONE).json()["id"]
        _complete(client, token, draft)
        _writes_on(factory)
        said = client.post(f"/v1/campaigns/v2/{draft}/launch", headers=head(token)).json()
        later = client.post(f"/v1/campaigns/v2/{draft}", headers=head(token), json={"name": "x"})
    assert said["ok"] is True, said
    assert said["status"] == "launched"
    assert said["campaign"] == f"customers/{CUSTOMER}/campaigns/777"
    assert [t.validate_only for t in door.sent] == [True, False], "checked by Google, then created"
    assert later.status_code == 409


def test_an_image_is_measured_then_put_in_the_asset_library(
    world: tuple[FastAPI, sessionmaker[Session], Google],
) -> None:
    app, factory, door = world
    with TestClient(app) as client:
        token = owner(client, factory)
        draft = client.post("/v1/campaigns/v2", headers=head(token), json=STEP_ONE).json()["id"]
        wrong = client.post(
            f"/v1/campaigns/v2/{draft}/images",
            headers=head(token),
            json={"shape": "square", "data": _png(1200, 628)},
        )
        assert wrong.status_code == 422 and "1:1 square" in wrong.json()["detail"]
        assert door.sent == []
        _writes_on(factory)
        real = door.mutate_together

        def named(together: Together) -> Created:
            made = real(together)
            if together.validate_only:
                return made
            return Created(names=(f"customers/{CUSTOMER}/assets/901",))

        door.mutate_together = named  # type: ignore[method-assign]
        made = client.post(
            f"/v1/campaigns/v2/{draft}/images",
            headers=head(token),
            json={"shape": "landscape", "data": _png(1200, 628), "name": "Hero"},
        )
    assert made.status_code == 200, made.text
    assert made.json()["asset"] == f"customers/{CUSTOMER}/assets/901"
    assert made.json()["width"] == 1200 and made.json()["url"] == "https://lh3/x.png"
    sent = [t for t in door.sent if not t.validate_only]
    assert sent[0].operations[0].resource_type == "asset"
    assert "imageAsset" in sent[0].operations[0].fields


def test_a_draft_nobody_published_can_be_discarded(
    world: tuple[FastAPI, sessionmaker[Session], Google],
) -> None:
    app, factory, _door = world
    with TestClient(app) as client:
        token = owner(client, factory)
        draft = client.post("/v1/campaigns/v2", headers=head(token), json=STEP_ONE).json()["id"]
        listed = client.get("/v1/campaigns/drafts", headers=head(token)).json()["drafts"]
        assert [d["id"] for d in listed] == [draft]
        gone = client.post(f"/v1/campaigns/v2/{draft}/discard", headers=head(token))
        after = client.get(f"/v1/campaigns/v2/{draft}", headers=head(token))
    assert gone.status_code == 200 and after.status_code == 404


def test_review_warns_when_the_account_cannot_pay(
    world: tuple[FastAPI, sessionmaker[Session], Google], monkeypatch: pytest.MonkeyPatch
) -> None:
    from ppcway.ads import setup

    monkeypatch.setattr(
        setup, "billing_ready", lambda customer_id, **k: {"known": True, "ready": False}
    )
    app, factory, _door = world
    with TestClient(app) as client:
        token = owner(client, factory)
        draft = client.post("/v1/campaigns/v2", headers=head(token), json=STEP_ONE).json()["id"]
        _complete(client, token, draft)
        said = client.post(f"/v1/campaigns/v2/{draft}/check", headers=head(token)).json()
    billing = [p for p in said["problems"] if p.get("code") == "billing"]
    assert said["ok"] is True, "Google would take it; it would just never serve"
    assert billing and billing[0]["blocks"] is False and "billing" in billing[0]["words"]


def test_a_refused_publish_says_googles_reasons(
    world: tuple[FastAPI, sessionmaker[Session], Google],
) -> None:
    app, factory, door = world
    real = door.mutate_together

    def refuse_for_real(together: Together) -> Created:
        if together.validate_only:
            return real(together)
        refused = GoogleRefused("Google refused the campaign")
        refused.problems = [
            {
                "resource_type": "campaign",
                "field": "name",
                "message": "Duplicate name.",
                "code": "z",
                "about": "the campaign",
            }
        ]
        raise refused

    door.mutate_together = refuse_for_real  # type: ignore[method-assign]
    with TestClient(app) as client:
        token = owner(client, factory)
        draft = client.post("/v1/campaigns/v2", headers=head(token), json=STEP_ONE).json()["id"]
        _complete(client, token, draft)
        _writes_on(factory)
        said = client.post(f"/v1/campaigns/v2/{draft}/launch", headers=head(token)).json()
    assert said["ok"] is False and said["status"] == "draft"
    assert [p["words"] for p in said["problems"]] == ["Google: Duplicate name."]


def test_every_type_google_lets_an_app_create_can_be_started(
    world: tuple[FastAPI, sessionmaker[Session], Google],
) -> None:
    app, factory, _door = world
    with TestClient(app) as client:
        token = owner(client, factory)
        made = {
            kind: client.post(
                "/v1/campaigns/v2", headers=head(token), json={**STEP_ONE, "type": kind}
            )
            for kind in ("PERFORMANCE_MAX", "DEMAND_GEN", "DISPLAY", "SHOPPING", "APP")
        }
    for kind, reply in made.items():
        assert reply.status_code == 201, (kind, reply.text)
    steps = {s["id"]: s["label"] for s in made["DEMAND_GEN"].json()["steps"]}
    assert steps["bidding"] == "Bidding and budget" and steps["ads"] == "Ads"
