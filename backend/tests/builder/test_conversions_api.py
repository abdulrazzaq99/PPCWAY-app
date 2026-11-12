"""Conversion setup through the endpoints the browser uses, Google faked at its edges.

The `world` fixture is the builder's: a signed-in owner with a connected
account and a fake door. Reads of the account are replaced; writes go through
the real gateway (switches, quota) to the fake door.
"""

# The `world` fixture is imported by name: pytest finds it that way, and ruff
# reads each test's use of it as a redefinition.
# ruff: noqa: F811

from __future__ import annotations

from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from ppcway.gateway import switch
from ppcway.gateway.port import Applied, Batch, Refused

from .test_builder_api import CUSTOMER, Google, head, owner, world  # noqa: F401

SUMMARY: dict[str, Any] = {
    "read": True,
    "reason": "",
    "tracking_id": "AW-555555",
    "actions": [],
    "importable": [],
    "sources": {"website": False, "app": False, "calls": False, "offline": False},
    "global_site_tag": "<script>gtag</script>",
}


@pytest.fixture(autouse=True)
def reads(monkeypatch: pytest.MonkeyPatch) -> None:
    from ppcway.ads import business
    from ppcway.ads import conversions as conv

    monkeypatch.setattr(conv, "measurement", lambda customer_id, **k: SUMMARY)
    monkeypatch.setattr(
        conv,
        "tag_on_site",
        lambda url, tracking, **k: conv.Tag(read=True, google_tag=True, this_account=True),
    )
    monkeypatch.setattr(
        "ppcway.api.app.known_business", lambda session, **k: business.Known(site="pdfezy.com")
    )


def _batches(door: Google) -> list[Batch]:
    sent: list[Batch] = []

    def mutate(batch: Batch) -> Applied:
        sent.append(batch)
        return Applied(
            landed=tuple(
                f"customers/{CUSTOMER}/conversionActions/{90 + n}"
                for n, _ in enumerate(batch.operations)
            )
        )

    door.mutate = mutate  # type: ignore[attr-defined]
    return sent


def _writes_on(factory: sessionmaker[Session]) -> None:
    with factory() as session:
        switch.set_gate(session, is_open=True, because="testing conversions", set_by=None)
        session.commit()


def test_the_summary_says_what_is_measured_and_offers_googles_sources(
    world: tuple[FastAPI, sessionmaker[Session], Google],
) -> None:
    app, factory, _door = world
    with TestClient(app) as client:
        token = owner(client, factory)
        said = client.get("/v1/conversions", headers=head(token)).json()
    assert said["connected"] and said["tracking_id"] == "AW-555555"
    assert said["website"] == "https://pdfezy.com"
    assert said["tag"]["this_account"] is True
    assert set(said["source_options"]) >= {"website", "calls_from_ads", "offline", "app_download"}
    assert said["sources"] == SUMMARY["sources"], "the measured map is not overwritten"
    assert said["may_change"] is True


def test_creating_actions_checks_first_then_sends_them_together(
    world: tuple[FastAPI, sessionmaker[Session], Google],
) -> None:
    app, factory, door = world
    sent = _batches(door)
    actions = [
        {
            "source": "website",
            "name": "Purchase",
            "category": "PURCHASE",
            "value": "different",
            "amount": 20,
        },
        {
            "source": "calls_from_ads",
            "name": "Calls from ads",
            "category": "PHONE_CALL_LEAD",
            "call_seconds": 60,
        },
    ]
    with TestClient(app) as client:
        token = owner(client, factory)
        bad = client.post(
            "/v1/conversions",
            headers=head(token),
            json={"actions": [{"source": "website", "name": "", "category": "PURCHASE"}]},
        )
        assert bad.status_code == 422 and "name" in bad.json()["detail"] and sent == []
        twice = client.post(
            "/v1/conversions", headers=head(token), json={"actions": [actions[0], actions[0]]}
        )
        assert twice.status_code == 422 and "same name" in twice.json()["detail"]
        closed = client.post("/v1/conversions", headers=head(token), json={"actions": actions})
        assert closed.status_code == 409, "the write switch applies to conversions too"
        _writes_on(factory)
        made = client.post("/v1/conversions", headers=head(token), json={"actions": actions})
    assert made.status_code == 200, made.text
    assert len(sent) == 1 and [op.fields["type"] for op in sent[0].operations] == [
        "WEBPAGE",
        "AD_CALL",
    ]
    assert made.json()["created_names"] == [
        f"customers/{CUSTOMER}/conversionActions/90",
        f"customers/{CUSTOMER}/conversionActions/91",
    ]


def test_a_refusal_from_google_names_the_action(
    world: tuple[FastAPI, sessionmaker[Session], Google],
) -> None:
    app, factory, door = world

    def mutate(batch: Batch) -> Applied:
        return Applied(
            landed=(None,),
            refused=(
                Refused(
                    at=0, code="conversionActionError.DUPLICATE_NAME", message="Name is taken."
                ),
            ),
        )

    door.mutate = mutate  # type: ignore[attr-defined]
    with TestClient(app) as client:
        token = owner(client, factory)
        _writes_on(factory)
        said = client.post(
            "/v1/conversions",
            headers=head(token),
            json={"actions": [{"source": "website", "name": "Purchase", "category": "PURCHASE"}]},
        ).json()
    assert said["refused"] == [
        {
            "name": "Purchase",
            "message": "Name is taken.",
            "code": "conversionActionError.DUPLICATE_NAME",
        }
    ]


def test_settings_import_and_goals_go_through_the_gateway(
    world: tuple[FastAPI, sessionmaker[Session], Google],
) -> None:
    app, factory, door = world
    sent = _batches(door)
    with TestClient(app) as client:
        token = owner(client, factory)
        _writes_on(factory)
        other = client.post(
            "/v1/conversions/update",
            headers=head(token),
            json={"resource": "customers/999/conversionActions/1", "change": {"primary": False}},
        )
        assert other.status_code == 422, "only this account's actions"
        client.post(
            "/v1/conversions/update",
            headers=head(token),
            json={
                "resource": f"customers/{CUSTOMER}/conversionActions/11",
                "change": {"primary": False},
            },
        )
        client.post(
            "/v1/conversions/import",
            headers=head(token),
            json={"resources": [f"customers/{CUSTOMER}/conversionActions/12"]},
        )
        client.post(
            "/v1/conversions/goal",
            headers=head(token),
            json={"category": "PURCHASE", "origin": "WEBSITE", "biddable": True},
        )
    kinds = [(b.operations[0].resource_type, b.operations[0].update_mask) for b in sent]
    assert kinds == [
        ("conversion_action", ("primary_for_goal",)),
        ("conversion_action", ("status",)),
        ("customer_conversion_goal", ("biddable",)),
    ]


def test_checking_the_tag_needs_a_real_address(
    world: tuple[FastAPI, sessionmaker[Session], Google],
) -> None:
    app, factory, _door = world
    with TestClient(app) as client:
        token = owner(client, factory)
        bad = client.get("/v1/conversions/tag?url=pdfezy", headers=head(token))
        good = client.get(
            "/v1/conversions/tag?url=https://pdfezy.com&tracking=AW-555555", headers=head(token)
        )
    assert bad.status_code == 422
    assert good.json()["google_tag"] is True
