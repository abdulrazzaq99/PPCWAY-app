"""Conversion setup's changes, as Google's Conversions screens make them.

The reads live in `ads.conversions`; this builds what is sent: new conversion
actions in Google's v25 shape, a change to one action's settings, switching on
an import, and making a goal an account default. Each is checked here first,
so what Google would refuse is said before anything is sent, and sent through
the gateway by the API, behind its switches.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final, Literal

from ppcway.ads.conversions import DATA_DRIVEN, LAST_CLICK, SOURCES
from ppcway.gateway.port import Doing, Operation

Value = Literal["same", "different", "none"]


@dataclass(frozen=True, slots=True)
class NewAction:
    """One conversion action as Google's "Create conversion actions" step takes it."""

    source: str
    name: str
    category: str
    value: Value = "same"
    amount: float = 0.0
    count: Literal["every", "one"] = "every"
    click_days: int = 30
    view_days: int = 1
    attribution: Literal["data_driven", "last_click"] = "data_driven"
    primary: bool = True
    call_seconds: int = 60
    app_id: str = ""


def problems_with(action: NewAction) -> list[str]:
    """What Google would refuse, said before anything is sent."""
    out: list[str] = []
    spec = SOURCES.get(action.source)
    if spec is None:
        return [f'"{action.source}" is not a way to measure conversions PPCWay can set up.']
    label = action.name.strip() or spec["label"]
    if not action.name.strip():
        out.append(f"{spec['label']}: give the conversion action a name.")
    if action.category not in spec["categories"]:
        out.append(f'"{label}": choose one of the goals Google offers for this source.')
    if action.value == "same" and action.amount < 0:
        out.append(f'"{label}": the value cannot be negative.')
    calls = bool(spec.get("call"))
    if not 1 <= action.click_days <= (60 if calls else 90):
        out.append(f'"{label}": the click-through window is 1 to {60 if calls else 90} days.')
    if not calls and not 1 <= action.view_days <= 30:
        out.append(f'"{label}": the view-through window is 1 to 30 days.')
    if calls and not 0 <= action.call_seconds <= 10_000:
        out.append(f'"{label}": a call counts after 0 to 10,000 seconds.')
    if spec.get("app") and not action.app_id.strip():
        out.append(f'"{label}": give the app\'s package name.')
    return out


def create_operations(actions: list[NewAction], *, currency: str) -> list[Operation]:
    """The conversion actions as creates, in Google's v25 shape."""
    ops: list[Operation] = []
    for action in actions:
        spec = SOURCES[action.source]
        calls = bool(spec.get("call"))
        fields: dict[str, Any] = {
            "name": action.name.strip()[:100],
            "type": spec["type"],
            "category": action.category,
            "status": "ENABLED",
            "primaryForGoal": action.primary,
            "countingType": "ONE_PER_CLICK" if action.count == "one" else "MANY_PER_CLICK",
            "clickThroughLookbackWindowDays": str(action.click_days),
            "attributionModelSettings": {
                "attributionModel": DATA_DRIVEN
                if action.attribution == "data_driven"
                else LAST_CLICK
            },
        }
        if spec["type"] in {"WEBPAGE", "GOOGLE_PLAY_DOWNLOAD", "GOOGLE_PLAY_IN_APP_PURCHASE"}:
            # Only conversions Google can see happen after an ad was viewed have
            # a view-through window: not calls, and not uploads.
            fields["viewThroughLookbackWindowDays"] = str(action.view_days)
        if calls:
            fields["phoneCallDurationSeconds"] = str(action.call_seconds)
        if spec.get("app"):
            fields["appId"] = action.app_id.strip()
        if action.value == "none":
            fields["valueSettings"] = {
                "defaultValue": 1.0,
                "defaultCurrencyCode": currency,
                "alwaysUseDefaultValue": True,
            }
        else:
            fields["valueSettings"] = {
                "defaultValue": float(action.amount or 0),
                "defaultCurrencyCode": currency,
                # A call has no transaction to report a value; Google requires
                # the same value for every call.
                "alwaysUseDefaultValue": action.value == "same" or calls,
            }
        ops.append(Operation(resource_type="conversion_action", doing=Doing.CREATE, fields=fields))
    return ops


#: The settings an existing action can change, by the name the screen uses.
_UPDATABLE: Final = {
    "name": "name",
    "category": "category",
    "status": "status",
    "primary": "primary_for_goal",
    "count": "counting_type",
    "click_days": "click_through_lookback_window_days",
    "view_days": "view_through_lookback_window_days",
    "attribution": "attribution_model_settings.attribution_model",
    "call_seconds": "phone_call_duration_seconds",
    "value": "value_settings",
}


def update_operation(resource: str, change: dict[str, Any], *, currency: str) -> Operation:
    """One action's settings changed, naming only what changed in the update mask."""
    fields: dict[str, Any] = {}
    mask: list[str] = []
    for key, value in change.items():
        if key not in _UPDATABLE:
            continue
        if key == "name":
            fields["name"] = str(value).strip()[:100]
        elif key == "category":
            fields["category"] = str(value)
        elif key == "status":
            if value not in {"ENABLED", "REMOVED"}:
                continue
            fields["status"] = value
        elif key == "primary":
            fields["primaryForGoal"] = bool(value)
        elif key == "count":
            fields["countingType"] = "ONE_PER_CLICK" if value == "one" else "MANY_PER_CLICK"
        elif key == "click_days":
            fields["clickThroughLookbackWindowDays"] = str(int(value))
        elif key == "view_days":
            fields["viewThroughLookbackWindowDays"] = str(int(value))
        elif key == "attribution":
            fields["attributionModelSettings"] = {
                "attributionModel": DATA_DRIVEN if value == "data_driven" else LAST_CLICK
            }
        elif key == "call_seconds":
            fields["phoneCallDurationSeconds"] = str(int(value))
        elif key == "value":
            mode = str((value or {}).get("mode", "same"))
            fields["valueSettings"] = {
                "defaultValue": 1.0 if mode == "none" else float((value or {}).get("amount") or 0),
                "defaultCurrencyCode": currency,
                "alwaysUseDefaultValue": mode != "different",
            }
        mask.append(_UPDATABLE[key])
    if not mask:
        raise ValueError("Nothing to change.")
    return Operation(
        resource_type="conversion_action",
        doing=Doing.UPDATE,
        resource_name=resource,
        fields=fields,
        update_mask=tuple(mask),
    )


def import_operation(resource: str) -> Operation:
    """Switch on a conversion Google lists from Google Analytics, Firebase or a partner."""
    return Operation(
        resource_type="conversion_action",
        doing=Doing.UPDATE,
        resource_name=resource,
        fields={"status": "ENABLED"},
        update_mask=("status",),
    )


def goal_operation(customer_id: str, category: str, origin: str, *, biddable: bool) -> Operation:
    """Make a goal an account default for bidding, or stop it being one."""
    return Operation(
        resource_type="customer_conversion_goal",
        doing=Doing.UPDATE,
        resource_name=f"customers/{customer_id}/customerConversionGoals/{category}~{origin}",
        fields={"biddable": biddable},
        update_mask=("biddable",),
    )
