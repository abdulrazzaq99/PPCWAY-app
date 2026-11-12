"""The shape of a mutation, and the one interface that may make one.

Ported from the proof of concept's `gateway/port.py`, which got the hard part
right and wrote down why.

**The hard part is partial failure.** Google's mutate endpoint, asked for
`partial_failure`, applies every operation that is valid and reports the rest
as per-operation errors rather than failing the batch. Blueprint §5.6 names
discarding that payload as a common and expensive bug: the platform believes it
created four hundred keywords when it created three hundred and eighty-six, and
nothing says otherwise until a merchant asks why half their ad group is
missing.

So `MutateResult` carries one entry per operation, at the same index, and uses
`None` rather than omission to mark one that did not land. `applied_count` is
derived from that convention. An implementation that returned a shorter list
would make `applied_count` lie quietly, which is why the invariant is stated
here and asserted by a test rather than left to each implementation's care.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable

#: Blueprint §5.4. Google's own ceiling for one mutate request.
MOST_OPERATIONS = 10_000

#: Google's resource-name URL scheme, by the name this codebase uses for each
#: resource. A property of the Google Ads API rather than of any one caller,
#: so it lives on the seam where both sides can reach it.
_PATHS = {
    "campaign": "campaigns",
    "campaign_budget": "campaignBudgets",
    "campaign_criterion": "campaignCriteria",
    "ad_group": "adGroups",
    "ad_group_criterion": "adGroupCriteria",
    "ad_group_ad": "adGroupAds",
    "shared_set": "sharedSets",
    "shared_criterion": "sharedCriteria",
    # What a whole new campaign needs beyond the first builder's six, since
    # 12 November: assets and where they are linked, Performance Max asset
    # groups and their signals, campaign goals, shared-list links, bid
    # adjustments and audiences (`builder.ops`).
    "asset": "assets",
    "customer_asset": "customerAssets",
    "campaign_asset": "campaignAssets",
    "ad_group_asset": "adGroupAssets",
    "asset_group": "assetGroups",
    "asset_group_asset": "assetGroupAssets",
    "asset_group_signal": "assetGroupSignals",
    "asset_group_listing_group_filter": "assetGroupListingGroupFilters",
    "asset_set": "assetSets",
    "asset_set_asset": "assetSetAssets",
    "campaign_asset_set": "campaignAssetSets",
    "campaign_conversion_goal": "campaignConversionGoals",
    "conversion_goal_campaign_config": "conversionGoalCampaignConfigs",
    "campaign_shared_set": "campaignSharedSets",
    "campaign_bid_modifier": "campaignBidModifiers",
    "ad_group_bid_modifier": "adGroupBidModifiers",
    "audience": "audiences",
    # Not mutate operations: Google takes these only at their own services,
    # after the campaign exists (new-customer bidding, `builder.publish`).
    "goal": "goals",
    "campaign_goal_config": "campaignGoalConfigs",
    # Conversion setup on Google's own steps (`ads.conversions`).
    "conversion_action": "conversionActions",
    "customer_conversion_goal": "customerConversionGoals",
}


def resource_name(customer_id: str, resource_type: str, entity_id: str) -> str:
    return f"customers/{customer_id}/{_PATHS[resource_type]}/{entity_id}"


def is_temporary(name: str) -> bool:
    """Whether a resource name is a placeholder for something created in the
    same request: Google's temporary ids are negative numbers."""
    return entity_id_of(name).startswith("-")


def entity_id_of(name: str) -> str:
    """The trailing id of a resource name, for re-addressing something Google
    told us about by name but which we must now name by id."""
    return name.rsplit("/", 1)[-1]


class Doing(StrEnum):
    CREATE = "create"
    UPDATE = "update"
    REMOVE = "remove"


@dataclass(frozen=True, slots=True)
class Operation:
    """One change to one thing."""

    resource_type: str
    doing: Doing
    #: The thing being changed, for an update or a remove. None for a create.
    resource_name: str | None = None
    fields: dict[str, Any] = field(default_factory=dict)
    #: Which fields of `fields` Google should actually read, for an update.
    #: Google ignores an update that does not name its own update mask, which
    #: is a silent no-op rather than an error -- the worst shape of failure.
    update_mask: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.resource_type not in _PATHS:
            raise ValueError(
                f"{self.resource_type!r} is not a resource this gateway knows how to"
                f" address. Adding one means adding its URL path, because a wrong"
                f" path is a request Google answers about a different thing."
            )
        if (
            self.doing is Doing.CREATE
            and self.resource_name
            and not is_temporary(self.resource_name)
        ):
            raise ValueError(
                "a create names nothing: Google assigns the resource name. The one"
                " exception is a temporary name, a negative id, which lets the other"
                " operations in the same request point at a thing not yet created."
            )
        if self.doing is not Doing.CREATE and not self.resource_name:
            raise ValueError(f"a {self.doing.value} has to say what it is changing")
        if self.doing is Doing.UPDATE and not self.update_mask:
            raise ValueError(
                "an update with no update mask is one Google accepts and ignores."
                " Name the fields it should read, or the change silently does nothing."
            )


@dataclass(frozen=True, slots=True)
class Batch:
    """One request to Google: everything in it, for one account."""

    customer_id: str
    operations: tuple[Operation, ...]
    #: True runs the operations through Google's validation and applies none.
    #: The pre-launch check in phase 4 is this, and so is every rehearsal.
    validate_only: bool = False
    #: Apply what is valid and report the rest. Always true: the alternative
    #: is one bad keyword costing a merchant the other three hundred.
    partial_failure: bool = True
    #: The action this batch carries out, so a retry of the same action cannot
    #: apply it twice.
    idempotency_key: str = ""

    def __post_init__(self) -> None:
        if not self.operations:
            raise ValueError("a batch with no operations is a request nobody meant to send")
        if len(self.operations) > MOST_OPERATIONS:
            raise ValueError(
                f"{len(self.operations)} operations is past Google's ceiling of"
                f" {MOST_OPERATIONS:,} for one request. Split it."
            )
        if any(op.resource_type != self.operations[0].resource_type for op in self.operations):
            # Google's mutate endpoint takes mixed operations, and this gateway
            # does not send them: a batch of one kind is one thing to retry,
            # one thing to undo, and one thing to explain.
            raise ValueError("a batch changes one kind of thing at a time")

    @property
    def how_many(self) -> int:
        return len(self.operations)


@dataclass(frozen=True, slots=True)
class Together:
    """Several kinds of change sent as one request that lands whole or not at all.

    A new campaign is a budget, a campaign, its places and language, ad groups,
    keywords and ads, and each points at something the request itself creates.
    Google's account-wide mutate takes them in one request, refers between them
    by temporary ids, and applies all of them or none -- so a campaign can never
    be left half built, and there is nothing to roll back.

    Partial failure is off on purpose, the opposite of `Batch`: here one refused
    ad is a reason to create nothing, because half a campaign is worse than no
    campaign.
    """

    customer_id: str
    operations: tuple[Operation, ...]
    #: True runs it through Google's checks and creates nothing. Every launch
    #: does this first, so a refusal is found before anything exists.
    validate_only: bool = False

    def __post_init__(self) -> None:
        if not self.operations:
            raise ValueError("a request with no operations is one nobody meant to send")
        if len(self.operations) > MOST_OPERATIONS:
            raise ValueError(
                f"{len(self.operations)} operations is past Google's ceiling of"
                f" {MOST_OPERATIONS:,} for one request."
            )

    @property
    def how_many(self) -> int:
        return len(self.operations)


@dataclass(frozen=True, slots=True)
class Created:
    """What a `Together` request made: one resource name per operation, in order."""

    names: tuple[str, ...]
    #: True when Google only checked it.
    checked_only: bool = False


@dataclass(frozen=True, slots=True)
class Refused:
    """One operation Google would not have, and why, in its own words."""

    at: int
    code: str
    message: str


@dataclass(frozen=True, slots=True)
class Applied:
    """What happened to a batch.

    `landed` has exactly one entry per operation in the batch, at the same
    index: the resource name when that operation landed, and `None` when it
    did not. An index that is `None` has a matching entry in `refused`.

    Omitting a failed operation instead of marking it `None` would make
    `how_many_landed` wrong without making it obviously wrong, which is the
    bug Blueprint §5.6 warns about. A test asserts the alignment.
    """

    landed: tuple[str | None, ...]
    refused: tuple[Refused, ...] = ()
    operations_used: int = 0

    def __post_init__(self) -> None:
        for one in self.refused:
            if not 0 <= one.at < len(self.landed):
                raise ValueError(
                    f"a refusal at index {one.at} does not line up with"
                    f" {len(self.landed)} operations: the indexes are how a caller"
                    f" tells which change failed."
                )
            if self.landed[one.at] is not None:
                raise ValueError(
                    f"operation {one.at} is both landed and refused. One of the two"
                    f" is wrong, and a caller cannot tell which."
                )

    @property
    def how_many_landed(self) -> int:
        """Operations that actually landed.

        Callers read this, never `len(operations)`. Believing the second is how
        a platform reports creating four hundred keywords when it created
        three hundred and eighty-six.
        """
        return sum(1 for name in self.landed if name is not None)

    @property
    def all_landed(self) -> bool:
        return not self.refused and all(name is not None for name in self.landed)


class GoogleRefused(RuntimeError):
    """Google would not take the request at all, as opposed to part of it.

    Defined on the seam rather than in the one implementation that raises it.
    An error any `Door` may raise is part of what a `Door` is, and a caller
    that had to import the real door to catch its errors would be a caller
    reaching past the seam -- which is the thing `tests/gateway/test_one_door.py`
    exists to stop.
    """

    #: Every error Google gave, when it gave more than a sentence: each with
    #: the operation's index, what it was about, the field and Google's code.
    #: Empty for a refusal that came with no detail.
    problems: list[dict[str, Any]]

    def __init__(self, *args: object) -> None:
        super().__init__(*args)
        self.problems = []


@runtime_checkable
class Door(Protocol):
    """The one door to Google. Only `ppcway.gateway` may hold one of these."""

    def mutate(self, batch: Batch) -> Applied: ...


@runtime_checkable
class Builds(Protocol):
    """The same door, for a request that creates several kinds of thing at once."""

    def mutate_together(self, together: Together) -> Created: ...
