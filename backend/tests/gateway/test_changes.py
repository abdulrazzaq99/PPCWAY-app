"""What an approved change sends: built from the log, for one account only.

R1 and R4 write their change into the row as plain data when it is proposed,
so what reaches Google is what the merchant was shown. These hold the
translation to the shape Google's mutate endpoints take, and the refusal to
send anything that names another account.
"""

from __future__ import annotations

import pytest

from ppcway.gateway.changes import Unsendable, batch_for, done_words
from ppcway.gateway.port import Doing
from ppcway.opt.models import OptimizationAction

CUSTOMER = "2580586343"


def _row(payload: dict[str, object] | None, **extra: object) -> OptimizationAction:
    return OptimizationAction(
        customer_id=CUSTOMER,
        kind="add_negative_keyword",
        target_label="pdf to word",
        payload=payload,
        idempotency_key="R1:abc",
        **extra,
    )


def _exclusion(*groups: str, text: str = "pdf to word") -> dict[str, object]:
    return {
        "change": "exclude_search",
        "text": text,
        "match_type": "EXACT",
        "ad_groups": [f"customers/{CUSTOMER}/adGroups/{g}" for g in groups],
    }


def test_a_search_is_excluded_as_an_exact_negative_in_every_ad_group_it_showed_in() -> None:
    batch = batch_for(_row(_exclusion("21", "22")))
    assert batch.customer_id == CUSTOMER
    assert batch.idempotency_key == "R1:abc"
    assert [op.doing for op in batch.operations] == [Doing.CREATE, Doing.CREATE]
    assert {op.resource_type for op in batch.operations} == {"ad_group_criterion"}
    assert batch.operations[0].fields == {
        "adGroup": f"customers/{CUSTOMER}/adGroups/21",
        "negative": True,
        "keyword": {"text": "pdf to word", "matchType": "EXACT"},
    }
    assert batch.operations[1].fields["adGroup"] == f"customers/{CUSTOMER}/adGroups/22"


def test_one_ad_group_named_twice_is_excluded_once() -> None:
    """A second identical negative is one Google refuses, failing the batch."""
    assert len(batch_for(_row(_exclusion("21", "21"))).operations) == 1


def test_a_pause_is_a_status_update_that_names_its_field() -> None:
    """An update with no mask is one Google accepts and ignores."""
    ad = f"customers/{CUSTOMER}/adGroupAds/21~77"
    batch = batch_for(_row({"change": "set_ad_status", "ad": ad, "status": "PAUSED"}))
    (op,) = batch.operations
    assert (op.resource_type, op.doing, op.resource_name) == ("ad_group_ad", Doing.UPDATE, ad)
    assert op.fields == {"status": "PAUSED"}
    assert op.update_mask == ("status",)


def test_putting_an_exclusion_back_removes_what_google_created() -> None:
    made = f"customers/{CUSTOMER}/adGroupCriteria/21~900"
    batch = batch_for(_row({"change": "remove_exclusions", "criteria": [made]}))
    (op,) = batch.operations
    assert (op.doing, op.resource_name) == (Doing.REMOVE, made)


def test_nothing_is_sent_that_names_another_account() -> None:
    """The guardrails compare account ids; this compares what Google acts on."""
    theirs = {
        "change": "exclude_search",
        "text": "pdf to word",
        "match_type": "EXACT",
        "ad_groups": ["customers/9999999999/adGroups/21"],
    }
    with pytest.raises(Unsendable, match="not in account 2580586343"):
        batch_for(_row(theirs))
    with pytest.raises(Unsendable, match="not in account"):
        batch_for(
            _row(
                {
                    "change": "set_ad_status",
                    "ad": "customers/9999999999/adGroupAds/1~2",
                    "status": "PAUSED",
                }
            )
        )


def test_a_remove_only_ever_points_at_an_exclusion() -> None:
    """A remove is final in Google. It is never aimed at a campaign or an ad."""
    with pytest.raises(Unsendable, match="not an exclusion"):
        batch_for(
            _row(
                {
                    "change": "remove_exclusions",
                    "criteria": [f"customers/{CUSTOMER}/campaigns/11"],
                }
            )
        )


def test_an_ad_is_never_removed_from_here() -> None:
    with pytest.raises(Unsendable, match="cannot be set to 'REMOVED'"):
        batch_for(
            _row(
                {
                    "change": "set_ad_status",
                    "ad": f"customers/{CUSTOMER}/adGroupAds/21~77",
                    "status": "REMOVED",
                }
            )
        )


@pytest.mark.parametrize(
    ("payload", "says"),
    [
        (None, "before PPCWay recorded what to send"),
        ({}, "before PPCWay recorded what to send"),
        ({"change": "raise_budget"}, "does not know how to send"),
        ({**_exclusion("21"), "text": " "}, "no search"),
        ({**_exclusion("21"), "match_type": "FUZZY"}, "not a match type"),
        ({**_exclusion(), "ad_groups": []}, "no ad group"),
    ],
)
def test_what_cannot_be_sent_says_why(payload: dict[str, object] | None, says: str) -> None:
    with pytest.raises(Unsendable, match=says):
        batch_for(_row(payload))


def test_the_words_say_what_was_done() -> None:
    assert (
        done_words(_row(_exclusion("21"))) == 'Searches for "pdf to word" no longer show your ads.'
    )
    assert "in all 2 ad groups" in done_words(_row(_exclusion("21", "22")))
    assert done_words(_row({"change": "set_ad_status", "ad": "a", "status": "PAUSED"})) == (
        "The ad is paused."
    )
    assert done_words(_row({"change": "remove_exclusions", "criteria": ["c"]})) == (
        'Searches for "pdf to word" can show your ads again.'
    )
