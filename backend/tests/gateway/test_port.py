"""The invariant partial failure rests on, and the shapes that cannot be built.

Blueprint §5.6 names the expensive bug: the platform believes it created four
hundred keywords when it created three hundred and eighty-six. These are the
tests that make that bug impossible to express.
"""

from __future__ import annotations

import pytest

from ppcway.gateway.port import (
    MOST_OPERATIONS,
    Applied,
    Batch,
    Doing,
    Operation,
    Refused,
    entity_id_of,
    resource_name,
)


def an_op(**over: object) -> Operation:
    fields: dict[str, object] = {
        "resource_type": "ad_group_criterion",
        "doing": Doing.CREATE,
        "fields": {"keyword": {"text": "boiler repair jobs"}},
    }
    fields.update(over)
    return Operation(**fields)  # type: ignore[arg-type]


def test_how_many_landed_counts_what_landed_not_what_was_sent() -> None:
    said = Applied(
        landed=("customers/1/adGroupCriteria/1~1", None, "customers/1/adGroupCriteria/1~3"),
        refused=(Refused(at=1, code="x.DUPLICATE", message="already there"),),
    )
    assert said.how_many_landed == 2
    assert len(said.landed) == 3, "and the sent count is still knowable"
    assert not said.all_landed


def test_everything_landing_is_its_own_answer() -> None:
    said = Applied(landed=("a", "b"))
    assert said.all_landed
    assert said.how_many_landed == 2


def test_a_refusal_that_does_not_line_up_cannot_be_built() -> None:
    """The indexes are how a caller tells which change failed."""
    with pytest.raises(ValueError, match="does not line up"):
        Applied(landed=(None,), refused=(Refused(at=7, code="x", message="y"),))


def test_an_operation_cannot_be_both_landed_and_refused() -> None:
    """One of the two is wrong and a caller cannot tell which."""
    with pytest.raises(ValueError, match="both landed and refused"):
        Applied(landed=("a",), refused=(Refused(at=0, code="x", message="y"),))


def test_an_update_without_an_update_mask_is_refused() -> None:
    """Google accepts one and ignores it: a silent no-op, the worst failure."""
    with pytest.raises(ValueError, match="accepts and ignores"):
        Operation(
            resource_type="campaign",
            doing=Doing.UPDATE,
            resource_name="customers/1/campaigns/11",
            fields={"status": "PAUSED"},
        )


def test_an_update_naming_its_fields_is_fine() -> None:
    op = Operation(
        resource_type="campaign",
        doing=Doing.UPDATE,
        resource_name="customers/1/campaigns/11",
        fields={"status": "PAUSED"},
        update_mask=("status",),
    )
    assert op.update_mask == ("status",)


def test_a_create_may_not_name_a_resource() -> None:
    with pytest.raises(ValueError, match="Google assigns the resource name"):
        an_op(resource_name="customers/1/adGroupCriteria/1~1")


def test_a_remove_has_to_say_what_it_removes() -> None:
    with pytest.raises(ValueError, match="say what it is changing"):
        an_op(doing=Doing.REMOVE)


def test_a_resource_the_gateway_cannot_address_is_refused() -> None:
    """A wrong URL path is a request Google answers about a different thing."""
    with pytest.raises(ValueError, match="not a resource this gateway knows"):
        an_op(resource_type="conversion_goal")


def test_an_empty_batch_is_refused() -> None:
    with pytest.raises(ValueError, match="nobody meant to send"):
        Batch(customer_id="1", operations=())


def test_a_batch_past_googles_ceiling_is_refused() -> None:
    with pytest.raises(ValueError, match="past Google's ceiling"):
        Batch(customer_id="1", operations=tuple(an_op() for _ in range(MOST_OPERATIONS + 1)))


def test_a_batch_changes_one_kind_of_thing() -> None:
    """One thing to retry, one thing to undo, one thing to explain."""
    with pytest.raises(ValueError, match="one kind of thing at a time"):
        Batch(
            customer_id="1",
            operations=(
                an_op(),
                an_op(resource_type="campaign", doing=Doing.CREATE, fields={"name": "x"}),
            ),
        )


def test_partial_failure_is_on_by_default() -> None:
    """The alternative is one bad keyword costing a merchant the other 300."""
    assert Batch(customer_id="1", operations=(an_op(),)).partial_failure


def test_resource_names_round_trip() -> None:
    name = resource_name("2580586343", "campaign", "11")
    assert name == "customers/2580586343/campaigns/11"
    assert entity_id_of(name) == "11"
