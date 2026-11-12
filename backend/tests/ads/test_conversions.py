"""Conversion setup on Google's own steps: what is read, what is sent, what is refused first.

Google is a `httpx.MockTransport` for the reads; the writes are checked as the
operations the gateway would send. Field names are v25's.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from ppcway.ads import conversions as conv
from ppcway.builder import conversions as changes
from ppcway.gateway.port import Doing

KEYS: dict[str, Any] = {"access_token": "a", "developer_token": "d"}
SEARCH = "/v25/customers/1234567890/googleAds:search"


def google(answers: dict[str, dict[str, Any]]) -> tuple[httpx.Client, list[str]]:
    """Answer each GAQL query by the resource it reads FROM."""
    asked: list[str] = []

    def handle(request: httpx.Request) -> httpx.Response:
        query = json.loads(request.content)["query"]
        asked.append(query)
        for key, body in answers.items():
            if key in query:
                return httpx.Response(200, json=body)
        return httpx.Response(200, json={"results": []})

    return httpx.Client(transport=httpx.MockTransport(handle)), asked


ACTIONS = {
    "results": [
        {
            "conversionAction": {
                "resourceName": "customers/1234567890/conversionActions/11",
                "id": "11",
                "name": "Contact form",
                "status": "ENABLED",
                "type": "WEBPAGE",
                "origin": "WEBSITE",
                "category": "SUBMIT_LEAD_FORM",
                "primaryForGoal": True,
                "countingType": "ONE_PER_CLICK",
                "valueSettings": {
                    "defaultValue": 1,
                    "defaultCurrencyCode": "CAD",
                    "alwaysUseDefaultValue": True,
                },
                "clickThroughLookbackWindowDays": "30",
                "viewThroughLookbackWindowDays": "1",
                "attributionModelSettings": {
                    "attributionModel": "GOOGLE_SEARCH_ATTRIBUTION_DATA_DRIVEN"
                },
                "ownerCustomer": "customers/1234567890",
                "tagSnippets": [
                    {
                        "type": "WEBPAGE",
                        "pageFormat": "HTML",
                        "globalSiteTag": "<script async src='https://www.googletagmanager.com/gtag/js?id=AW-555555'></script>",
                        "eventSnippet": "<script>gtag('event','conversion',{'send_to':'AW-555555/abc'});</script>",
                    }
                ],
            }
        },
        {
            "conversionAction": {
                "resourceName": "customers/1234567890/conversionActions/12",
                "name": "GA4 purchase",
                "status": "HIDDEN",
                "type": "GOOGLE_ANALYTICS_4_PURCHASE",
                "category": "PURCHASE",
            }
        },
    ]
}

SETTING = {
    "results": [
        {
            "customer": {
                "conversionTrackingSetting": {
                    "conversionTrackingId": "555555",
                    "conversionTrackingStatus": "CONVERSION_TRACKING_MANAGED_BY_SELF",
                }
            }
        }
    ]
}

RECENT = {
    "results": [
        {
            "segments": {"conversionAction": "customers/1234567890/conversionActions/11"},
            "metrics": {"allConversions": 4.0},
        }
    ]
}


def test_the_summary_reads_the_tag_every_action_and_what_can_be_imported() -> None:
    client, asked = google(
        {
            "FROM conversion_action": ACTIONS,
            "conversion_tracking_setting": SETTING,
            "segments.conversion_action": RECENT,
        }
    )
    said = conv.measurement("1234567890", client=client, **KEYS)
    assert said["tracking_id"] == "AW-555555"
    assert [a["name"] for a in said["actions"]] == ["Contact form"]
    form = said["actions"][0]
    assert form["state"] == "Recording conversions" and form["recent"] == 4.0
    assert form["source"] == "website" and form["source_label"] == "Website (Google tag)"
    assert form["editable"] is True and form["snippets"][0]["event_snippet"].startswith("<script>")
    assert [a["name"] for a in said["importable"]] == ["GA4 purchase"]
    assert said["sources"] == {"website": True, "app": False, "calls": False, "offline": False}
    assert "googletagmanager" in said["global_site_tag"]
    assert any("status != 'REMOVED'" in q for q in asked)


def test_a_refused_read_says_so_and_lists_nothing() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"error": {"message": "nope"}})

    said = conv.measurement(
        "1234567890", client=httpx.Client(transport=httpx.MockTransport(handle)), **KEYS
    )
    assert said["read"] is False and said["actions"] == []


def test_website_actions_are_webpage_with_googles_settings() -> None:
    (op,) = changes.create_operations(
        [
            changes.NewAction(
                source="website", name="Purchase", category="PURCHASE", value="different", amount=25
            )
        ],
        currency="CAD",
    )
    assert op.resource_type == "conversion_action" and op.doing is Doing.CREATE
    assert op.fields == {
        "name": "Purchase",
        "type": "WEBPAGE",
        "category": "PURCHASE",
        "status": "ENABLED",
        "primaryForGoal": True,
        "countingType": "MANY_PER_CLICK",
        "clickThroughLookbackWindowDays": "30",
        "viewThroughLookbackWindowDays": "1",
        "attributionModelSettings": {"attributionModel": "GOOGLE_SEARCH_ATTRIBUTION_DATA_DRIVEN"},
        "valueSettings": {
            "defaultValue": 25.0,
            "defaultCurrencyCode": "CAD",
            "alwaysUseDefaultValue": False,
        },
    }


def test_call_actions_have_a_call_length_and_no_view_window() -> None:
    (op,) = changes.create_operations(
        [
            changes.NewAction(
                source="calls_from_ads",
                name="Calls",
                category="PHONE_CALL_LEAD",
                value="different",
                call_seconds=90,
            )
        ],
        currency="CAD",
    )
    assert op.fields["type"] == "AD_CALL"
    assert op.fields["phoneCallDurationSeconds"] == "90"
    assert "viewThroughLookbackWindowDays" not in op.fields
    assert op.fields["valueSettings"]["alwaysUseDefaultValue"] is True, (
        "Google requires it for calls"
    )


def test_app_and_offline_actions() -> None:
    app, offline = changes.create_operations(
        [
            changes.NewAction(
                source="app_download", name="Installs", category="DOWNLOAD", app_id="com.pdfezy.app"
            ),
            changes.NewAction(
                source="offline",
                name="Qualified",
                category="QUALIFIED_LEAD",
                count="one",
                value="none",
            ),
        ],
        currency="CAD",
    )
    assert app.fields["type"] == "GOOGLE_PLAY_DOWNLOAD" and app.fields["appId"] == "com.pdfezy.app"
    assert (
        offline.fields["type"] == "UPLOAD_CLICKS"
        and offline.fields["countingType"] == "ONE_PER_CLICK"
    )
    assert offline.fields["valueSettings"]["alwaysUseDefaultValue"] is True


@pytest.mark.parametrize(
    ("action", "says"),
    [
        (
            changes.NewAction(source="website", name="", category="PURCHASE"),
            "give the conversion action a name",
        ),
        (
            changes.NewAction(source="website", name="X", category="PHONE_CALL_LEAD"),
            "choose one of the goals",
        ),
        (
            changes.NewAction(source="website", name="X", category="PURCHASE", click_days=120),
            "1 to 90 days",
        ),
        (
            changes.NewAction(
                source="calls_from_ads", name="X", category="PHONE_CALL_LEAD", click_days=75
            ),
            "1 to 60 days",
        ),
        (changes.NewAction(source="app_purchase", name="X", category="PURCHASE"), "package name"),
        (
            changes.NewAction(source="nowhere", name="X", category="PURCHASE"),
            "not a way to measure",
        ),
    ],
)
def test_what_google_would_refuse_is_said_first(action: changes.NewAction, says: str) -> None:
    assert any(says in p for p in changes.problems_with(action))


def test_a_settings_change_names_only_what_changed() -> None:
    op = changes.update_operation(
        "customers/1/conversionActions/11",
        {"primary": False, "click_days": 60, "unknown": 1},
        currency="CAD",
    )
    assert op.doing is Doing.UPDATE
    assert op.fields == {"primaryForGoal": False, "clickThroughLookbackWindowDays": "60"}
    assert op.update_mask == ("primary_for_goal", "click_through_lookback_window_days")
    with pytest.raises(ValueError):
        changes.update_operation("customers/1/conversionActions/11", {"unknown": 1}, currency="CAD")


def test_import_and_account_goal_operations() -> None:
    imp = changes.import_operation("customers/1/conversionActions/12")
    assert imp.fields == {"status": "ENABLED"} and imp.update_mask == ("status",)
    goal = changes.goal_operation("1", "PURCHASE", "WEBSITE", biddable=True)
    assert goal.resource_name == "customers/1/customerConversionGoals/PURCHASE~WEBSITE"
    assert goal.fields == {"biddable": True} and goal.update_mask == ("biddable",)


def test_the_tag_is_found_in_the_page_itself() -> None:
    page = (
        "<head><script async src='https://www.googletagmanager.com/gtag/js?id=AW-555555'></script>"
        "<script>gtag('config','G-ABC1234')</script></head>"
    )
    tag = conv.tag_on_site("https://pdfezy.com", "AW-555555", fetch=lambda url, **k: page)
    assert tag.read and tag.google_tag and tag.this_account and not tag.tag_manager
    assert tag.found_ids == ("AW-555555", "G-ABC1234")
    other = conv.tag_on_site("https://pdfezy.com", "AW-999999", fetch=lambda url, **k: page)
    assert other.google_tag and not other.this_account
    gtm = conv.tag_on_site(
        "https://x.com",
        "AW-1",
        fetch=lambda url, **k: "<script src='https://www.googletagmanager.com/gtm.js?id=GTM-AB12'>",
    )
    assert gtm.tag_manager


def test_an_unreadable_page_is_could_not_tell() -> None:
    def broken(url: str, **k: Any) -> str:
        raise OSError("down")

    assert conv.tag_on_site("https://x.com", "AW-1", fetch=broken).read is False
    assert conv.tag_on_site("https://x.com", "AW-1", fetch=lambda url, **k: None).read is False


def test_uploads_get_no_view_through_window() -> None:
    offline, uploads = changes.create_operations(
        [
            changes.NewAction(source="offline", name="Qualified", category="QUALIFIED_LEAD"),
            changes.NewAction(
                source="call_uploads", name="Uploaded calls", category="PHONE_CALL_LEAD"
            ),
        ],
        currency="CAD",
    )
    assert "viewThroughLookbackWindowDays" not in offline.fields
    assert "viewThroughLookbackWindowDays" not in uploads.fields


def test_an_action_a_manager_owns_is_not_editable_here() -> None:
    managed = {
        "results": [
            {
                "conversionAction": {
                    **ACTIONS["results"][0]["conversionAction"],
                    "ownerCustomer": "customers/7777777777",
                }
            }
        ]
    }
    client, _ = google({"FROM conversion_action": managed, "conversion_tracking_setting": SETTING})
    said = conv.measurement("1234567890", client=client, **KEYS)
    assert said["actions"][0]["editable"] is False
