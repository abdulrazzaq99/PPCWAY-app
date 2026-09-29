import json

import httpx
import pytest

from ppcway.audit.places import (
    DETAILS_ENDPOINT,
    GEOCODE_ENDPOINT,
    SEARCH_ENDPOINT,
    PlacesError,
    details_mask,
    find_businesses,
    names_match,
    parse_listing,
    place_details,
    search_body,
)

MISSISSAUGA = {
    "status": "OK",
    "results": [{"geometry": {"location": {"lat": 43.589, "lng": -79.644}}}],
}


def _place(pid: str, name: str, **extra: object) -> dict[str, object]:
    return {"id": pid, "displayName": {"text": name}, **extra}


def test_the_name_must_carry_every_word_typed() -> None:
    assert names_match("Alpha Plumbing", "Alpha Plumbing & Drains")
    assert names_match("alpha plumbing and drains", "ALPHA PLUMBING & DRAINS")
    assert not names_match("Alpha Plumbing", "Alpine Plumbing")
    assert not names_match("", "Alpha Plumbing")


def test_a_listing_is_read_with_its_gaps_left_empty() -> None:
    li = parse_listing(
        _place(
            "p1",
            "Alpha Plumbing",
            rating=4.6,
            userRatingCount=87,
            pureServiceAreaBusiness=True,
            currentOpeningHours={"openNow": True},
            primaryTypeDisplayName={"text": "Plumber"},
        ),
        "alpha plumbing",
    )
    assert li.rating == 4.6 and li.reviews == 87 and li.service_area_only and li.open_now is True
    assert li.category == "Plumber" and li.name_match and li.website == "" and li.lat is None
    bare = parse_listing(_place("p2", "Somebody"))
    assert (
        bare.rating is None and bare.reviews == 0 and bare.open_now is None and not bare.name_match
    )


def test_the_town_leans_the_search_and_never_fences_it() -> None:
    body = search_body("Alpha Plumbing", (43.589, -79.644), "ca")
    assert body["textQuery"] == "Alpha Plumbing"
    assert body["includePureServiceAreaBusinesses"] is True
    assert "locationRestriction" not in body
    assert body["locationBias"]["circle"]["radius"] == 50_000.0
    assert "locationBias" not in search_body("Alpha Plumbing", None, "ca")


def test_pages_are_followed_and_name_matches_come_first() -> None:
    seen: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url).startswith(GEOCODE_ENDPOINT):
            return httpx.Response(200, json=MISSISSAUGA)
        assert str(request.url) == SEARCH_ENDPOINT
        assert request.headers["X-Goog-FieldMask"].endswith("nextPageToken")
        body = json.loads(request.content)
        seen.append(body)
        if "pageToken" not in body:
            return httpx.Response(
                200,
                json={
                    "places": [_place("a", "Best Drains"), _place("b", "Alpha Plumbing")],
                    "nextPageToken": "t2",
                },
            )
        return httpx.Response(200, json={"places": [_place("c", "Alpha Plumbing Services")]})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        found = find_businesses("Alpha Plumbing", city="Mississauga", api_key="k", client=client)
    assert [li.place_id for li in found] == ["b", "c", "a"]
    assert seen[1]["pageToken"] == "t2" and seen[0]["locationBias"] == seen[1]["locationBias"]


def test_a_refusal_names_googles_reason() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            403, json={"error": {"status": "PERMISSION_DENIED", "message": "API not enabled"}}
        )

    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as client,
        pytest.raises(PlacesError, match="API not enabled"),
    ):
        find_businesses("Alpha Plumbing", api_key="k", client=client)


def test_one_listing_is_read_by_its_id_with_a_mask_of_single_fields() -> None:
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["mask"] = request.headers["X-Goog-FieldMask"]
        seen["key"] = request.headers["X-Goog-Api-Key"]
        return httpx.Response(
            200, json=_place("p9", "Alpha Plumbing", rating=5.0, userRatingCount=7)
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        li = place_details("p9", api_key="k", client=client)

    assert li is not None and li.place_id == "p9" and li.rating == 5.0 and li.reviews == 7
    assert seen["url"] == DETAILS_ENDPOINT + "p9" and seen["key"] == "k"
    # The page mask names "places.rating"; one place names "rating".
    assert "rating" in seen["mask"] and "places." not in seen["mask"]
    assert "nextPageToken" not in details_mask()


@pytest.mark.parametrize("code", [404, 400])
def test_an_id_google_does_not_know_reads_as_nothing(code: int) -> None:
    """404 is an id Google dropped, 400 one that was never its own. Same to a screen."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(code, json={"error": {"message": "Requested entity was not found."}})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        assert place_details("gone", api_key="k", client=client) is None


def test_a_refused_town_lookup_never_quotes_the_key() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"error_message": "This API key is not authorized"})

    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as client,
        pytest.raises(PlacesError) as refused,
    ):
        find_businesses("Alpha Plumbing", city="Mississauga", api_key="secret-key", client=client)
    assert "secret-key" not in str(refused.value)
