"""Conversions, set up the way Google Ads' own Conversions screens set them up.

On 12 November the owner asked for conversion setup "same as it is in the
Google Ads account". Google's current flow ("Welcome to a simpler conversion
measurement setup") has three steps:

1. **Get started**: choose the data sources where customers act. Conversions
   on a website (measured with the Google tag, or imported from Google
   Analytics), on an app, from phone calls (calls from ads, calls from website
   visits, calls via uploads) and offline (a CRM, a file, the API).
2. **Create conversion actions** for each source, each with its category,
   value, count, windows, attribution and whether it is a primary action.
3. **Summary**: what was created and how to install the tag.

The API keeps no "data source" object: a source is the kind of conversion
action measuring it. So the sources are read off the actions (`sources`), and
creating one is creating the actions behind it (`builder.conversions`), through
`ConversionActionService` (`POST /v25/customers/{id}/conversionActions:mutate`).
What the API cannot create is said where it comes up: Google Analytics and
Firebase conversions are imported by switching a hidden action on,
and codeless URL conversions, lead form and store conversions are read only.

This module only reads. The changes (new actions, settings, imports, goals)
are built in `builder.conversions`, because only the packages that act may
reach the gateway (`tests/gateway/test_one_door.py`).

Field names are v25's (resources/conversion_action.proto, read 12 November).
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Final

import httpx

from ppcway.ads.sync import _ask

log = logging.getLogger(__name__)

#: Google's category names, as its Conversions screens word them.
CATEGORY_LABEL: Final[dict[str, str]] = {
    "PURCHASE": "Purchase",
    "ADD_TO_CART": "Add to cart",
    "BEGIN_CHECKOUT": "Begin checkout",
    "SUBSCRIBE_PAID": "Subscribe",
    "SUBMIT_LEAD_FORM": "Submit lead form",
    "BOOK_APPOINTMENT": "Book appointment",
    "SIGNUP": "Sign-up",
    "REQUEST_QUOTE": "Request quote",
    "GET_DIRECTIONS": "Get directions",
    "OUTBOUND_CLICK": "Outbound click",
    "CONTACT": "Contact",
    "PHONE_CALL_LEAD": "Phone call lead",
    "PAGE_VIEW": "Page view",
    "ENGAGEMENT": "Engagement",
    "DOWNLOAD": "Download",
    "IMPORTED_LEAD": "Imported lead",
    "QUALIFIED_LEAD": "Qualified lead",
    "CONVERTED_LEAD": "Converted lead",
    "STORE_VISIT": "Store visit",
    "STORE_SALE": "Store sale",
    "DEFAULT": "Other",
}

#: The ways to measure, by Google's data sources, and the action type each one is.
SOURCES: Final[dict[str, dict[str, Any]]] = {
    "website": {
        "type": "WEBPAGE",
        "label": "Conversions on a website",
        "categories": [
            "PURCHASE",
            "ADD_TO_CART",
            "BEGIN_CHECKOUT",
            "SUBSCRIBE_PAID",
            "SUBMIT_LEAD_FORM",
            "BOOK_APPOINTMENT",
            "SIGNUP",
            "REQUEST_QUOTE",
            "GET_DIRECTIONS",
            "OUTBOUND_CLICK",
            "CONTACT",
            "PAGE_VIEW",
            "DEFAULT",
        ],
    },
    "calls_from_ads": {
        "type": "AD_CALL",
        "label": "Calls from ads",
        "categories": ["PHONE_CALL_LEAD"],
        "call": True,
    },
    "calls_from_website": {
        "type": "WEBSITE_CALL",
        "label": "Calls from website visits",
        "categories": ["PHONE_CALL_LEAD"],
        "call": True,
    },
    "call_uploads": {
        "type": "UPLOAD_CALLS",
        "label": "Calls via uploads",
        "categories": ["PHONE_CALL_LEAD"],
    },
    "offline": {
        "type": "UPLOAD_CLICKS",
        "label": "Conversions offline",
        "categories": [
            "IMPORTED_LEAD",
            "QUALIFIED_LEAD",
            "CONVERTED_LEAD",
            "PURCHASE",
            "SUBMIT_LEAD_FORM",
            "BOOK_APPOINTMENT",
            "SIGNUP",
            "DEFAULT",
        ],
    },
    "app_download": {
        "type": "GOOGLE_PLAY_DOWNLOAD",
        "label": "App installs from Google Play",
        "categories": ["DOWNLOAD"],
        "app": True,
    },
    "app_purchase": {
        "type": "GOOGLE_PLAY_IN_APP_PURCHASE",
        "label": "In-app purchases from Google Play",
        "categories": ["PURCHASE"],
        "app": True,
    },
}

#: Which data source each kind of action belongs to, for the summary.
SOURCE_OF_TYPE: Final[dict[str, str]] = {
    "WEBPAGE": "website",
    "WEBPAGE_CODELESS": "website",
    "GOOGLE_ANALYTICS_4_CUSTOM": "website",
    "GOOGLE_ANALYTICS_4_PURCHASE": "website",
    "GOOGLE_ANALYTICS_4_GENERATE_LEAD": "website",
    "GOOGLE_ANALYTICS_4_QUALIFY_LEAD": "website",
    "GOOGLE_ANALYTICS_4_CLOSE_CONVERT_LEAD": "website",
    "AD_CALL": "calls",
    "WEBSITE_CALL": "calls",
    "CLICK_TO_CALL": "calls",
    "UPLOAD_CALLS": "calls",
    "UPLOAD_CLICKS": "offline",
    "GOOGLE_PLAY_DOWNLOAD": "app",
    "GOOGLE_PLAY_IN_APP_PURCHASE": "app",
    "LEAD_FORM_SUBMIT": "google",
    "GOOGLE_HOSTED": "google",
    "STORE_VISITS": "store",
    "STORE_SALES": "store",
}

#: What Google calls each kind of action in its "Source" column.
TYPE_LABEL: Final[dict[str, str]] = {
    "WEBPAGE": "Website (Google tag)",
    "WEBPAGE_CODELESS": "Website (URL rules)",
    "AD_CALL": "Calls from ads",
    "WEBSITE_CALL": "Calls from website",
    "CLICK_TO_CALL": "Clicks to call",
    "UPLOAD_CALLS": "Call uploads",
    "UPLOAD_CLICKS": "Offline import",
    "GOOGLE_PLAY_DOWNLOAD": "Google Play",
    "GOOGLE_PLAY_IN_APP_PURCHASE": "Google Play",
    "LEAD_FORM_SUBMIT": "Lead form",
    "GOOGLE_HOSTED": "Google hosted",
    "STORE_VISITS": "Store visits",
    "STORE_SALES": "Store sales",
}

#: Imported from Google Analytics, Firebase or an app analytics partner: these
#: cannot be created through the API, only switched on once Google lists them.
IMPORTED_PREFIXES: Final = ("GOOGLE_ANALYTICS_4_", "FIREBASE_", "THIRD_PARTY_APP_ANALYTICS_")

DATA_DRIVEN: Final = "GOOGLE_SEARCH_ATTRIBUTION_DATA_DRIVEN"
LAST_CLICK: Final = "GOOGLE_ADS_LAST_CLICK"


@contextmanager
def _client(client: httpx.Client | None) -> Iterator[httpx.Client]:
    if client is not None:
        yield client
        return
    with httpx.Client(timeout=httpx.Timeout(30)) as made:
        yield made


def _rows(
    customer_id: str, query: str, keys: dict[str, Any], client: httpx.Client
) -> tuple[list[dict[str, Any]], str]:
    return _ask(
        customer_id,
        query,
        access_token=keys["access_token"],
        developer_token=keys["developer_token"],
        login_customer_id=keys.get("login_customer_id"),
        api_version=keys.get("api_version", "v25"),
        client=client,
    )


def _tracking_id(setting: dict[str, Any]) -> str:
    raw = setting.get("crossAccountConversionTrackingId") or setting.get("conversionTrackingId")
    return f"AW-{raw}" if raw else ""


def _action(row: dict[str, Any], recent: dict[str, float], customer_id: str = "") -> dict[str, Any]:
    a = row.get("conversionAction") or {}
    value = a.get("valueSettings") or {}
    kind = str(a.get("type", ""))
    status = str(a.get("status", ""))
    resource = str(a.get("resourceName", ""))
    counted = recent.get(resource, 0.0)
    if status == "HIDDEN":
        state = "Not imported"
    elif counted > 0:
        state = "Recording conversions"
    elif status == "ENABLED":
        state = "No recent conversions"
    else:
        state = status.title()
    snippets = [
        {
            "type": str(s.get("type", "")),
            "page_format": str(s.get("pageFormat", "")),
            "global_site_tag": str(s.get("globalSiteTag", "")),
            "event_snippet": str(s.get("eventSnippet", "")),
        }
        for s in a.get("tagSnippets") or []
    ]
    return {
        "resource": resource,
        "id": str(a.get("id", "")),
        "name": str(a.get("name", "")),
        "status": status,
        "state": state,
        "type": kind,
        "source": SOURCE_OF_TYPE.get(
            kind, "app" if kind.startswith(("FIREBASE_", "THIRD_PARTY_")) else "other"
        ),
        "source_label": TYPE_LABEL.get(kind, kind.replace("_", " ").title()),
        "origin": str(a.get("origin", "")),
        "category": str(a.get("category", "")),
        "category_label": CATEGORY_LABEL.get(str(a.get("category", "")), "Other"),
        "primary": bool(a.get("primaryForGoal", False)),
        "counting": str(a.get("countingType", "")),
        "value": {
            "default": value.get("defaultValue"),
            "currency": str(value.get("defaultCurrencyCode", "")),
            "always": bool(value.get("alwaysUseDefaultValue", False)),
        },
        "click_days": int(a.get("clickThroughLookbackWindowDays") or 0) or None,
        "view_days": int(a.get("viewThroughLookbackWindowDays") or 0) or None,
        "attribution": str((a.get("attributionModelSettings") or {}).get("attributionModel", "")),
        "call_seconds": int(a.get("phoneCallDurationSeconds") or 0) or None,
        "app_id": str(a.get("appId", "")),
        "imported": kind.startswith(IMPORTED_PREFIXES),
        # Only this account's own actions: one a manager account owns is
        # managed there, and Google refuses changes made from here.
        "editable": str(a.get("ownerCustomer", "")) == f"customers/{customer_id}"
        and not kind.startswith(IMPORTED_PREFIXES),
        "recent": counted,
        "snippets": snippets,
    }


_ACTION_FIELDS: Final = """conversion_action.resource_name, conversion_action.id,
    conversion_action.name, conversion_action.status, conversion_action.type,
    conversion_action.origin, conversion_action.category,
    conversion_action.primary_for_goal, conversion_action.counting_type,
    conversion_action.value_settings.default_value,
    conversion_action.value_settings.default_currency_code,
    conversion_action.value_settings.always_use_default_value,
    conversion_action.click_through_lookback_window_days,
    conversion_action.view_through_lookback_window_days,
    conversion_action.attribution_model_settings.attribution_model,
    conversion_action.phone_call_duration_seconds, conversion_action.app_id,
    conversion_action.owner_customer, conversion_action.tag_snippets"""


def measurement(
    customer_id: str,
    *,
    access_token: str,
    developer_token: str,
    login_customer_id: str | None = None,
    api_version: str = "v25",
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    """The account's conversion measurement, as Google's Conversions summary shows it.

    The Google tag's id, every conversion action with its settings, tag code and
    whether it counted anything in the last 30 days, the actions Google lists
    for import, and which data sources are already measured.
    """
    keys = {
        "access_token": access_token,
        "developer_token": developer_token,
        "login_customer_id": login_customer_id,
        "api_version": api_version,
    }
    with _client(client) as c:
        setting_rows, trouble = _rows(
            customer_id,
            """SELECT customer.conversion_tracking_setting.conversion_tracking_id,
                customer.conversion_tracking_setting.cross_account_conversion_tracking_id,
                customer.conversion_tracking_setting.conversion_tracking_status,
                customer.conversion_tracking_setting.accepted_customer_data_terms
            FROM customer""",
            keys,
            c,
        )
        if trouble:
            log.warning("Google would not say how %s tracks conversions: %s", customer_id, trouble)
            return {"read": False, "reason": trouble, "actions": [], "importable": []}
        action_rows, trouble = _rows(
            customer_id,
            f"SELECT {_ACTION_FIELDS} FROM conversion_action"
            " WHERE conversion_action.status != 'REMOVED'",
            keys,
            c,
        )
        recent_rows, _quiet = _rows(
            customer_id,
            """SELECT segments.conversion_action, metrics.all_conversions FROM customer
            WHERE segments.date DURING LAST_30_DAYS""",
            keys,
            c,
        )
    recent: dict[str, float] = {}
    for row in recent_rows:
        name = str((row.get("segments") or {}).get("conversionAction", ""))
        recent[name] = recent.get(name, 0.0) + float(
            (row.get("metrics") or {}).get("allConversions") or 0
        )
    setting = (setting_rows[0].get("customer") or {}).get("conversionTrackingSetting") or {}
    everything = [_action(row, recent, customer_id) for row in action_rows]
    actions = [a for a in everything if a["status"] != "HIDDEN"]
    importable = [a for a in everything if a["status"] == "HIDDEN" and a["imported"]]
    measured = {a["source"] for a in actions if a["status"] == "ENABLED"}
    return {
        "read": True,
        "reason": trouble,
        "tracking_id": _tracking_id(setting),
        "tracking_status": str(setting.get("conversionTrackingStatus", "")),
        "data_terms": bool(setting.get("acceptedCustomerDataTerms", False)),
        "actions": actions,
        "importable": importable,
        "sources": {
            "website": "website" in measured,
            "app": "app" in measured,
            "calls": "calls" in measured,
            "offline": "offline" in measured,
        },
        "global_site_tag": next(
            (s["global_site_tag"] for a in actions for s in a["snippets"] if s["global_site_tag"]),
            "",
        ),
    }


@dataclass(frozen=True, slots=True)
class Tag:
    """What a page's own markup says about the Google tag."""

    read: bool
    google_tag: bool = False
    this_account: bool = False
    tag_manager: bool = False
    found_ids: tuple[str, ...] = ()


_IDS = re.compile(r"\b(AW-\d{6,}|G-[A-Z0-9]{6,}|GTM-[A-Z0-9]{4,}|GT-[A-Z0-9]{6,})\b")


def tag_on_site(url: str, tracking_id: str, *, fetch: Any | None = None) -> Tag:
    """Whether the page at `url` loads the Google tag, and this account's.

    Google's screen says "pdfezy.com via Google Tag" when it sees the tag
    firing; PPCWay cannot see it fire, so it reads the page for `gtag/js`, the
    account's `AW-` id and a Tag Manager container. A tag added through Tag
    Manager does not show in the page itself, which the screen says.
    """
    from ppcway.crawler.fetch import fetch_html

    read = fetch or fetch_html
    try:
        html = read(url, timeout_seconds=8.0)
    except Exception as exc:  # noqa: BLE001 - an unreadable page is "could not tell", not a failure
        log.info("page %s not read for the tag: %s", url, type(exc).__name__)
        return Tag(read=False)
    if not html:
        return Tag(read=False)
    found = tuple(dict.fromkeys(_IDS.findall(html)))
    return Tag(
        read=True,
        google_tag="googletagmanager.com/gtag/js" in html
        or any(i.startswith("AW-") for i in found),
        this_account=bool(tracking_id) and tracking_id in found,
        tag_manager="googletagmanager.com/gtm.js" in html
        or any(i.startswith("GTM-") for i in found),
        found_ids=found,
    )
