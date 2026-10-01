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
    nearby_rivals,
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


def test_hours_photos_and_the_twenty_four_hour_case_are_read() -> None:
    li = parse_listing(
        _place(
            "p3",
            "Night Owl Plumbing",
            photos=[{"name": "a"}, {"name": "b"}],
            regularOpeningHours={"periods": [{"open": {"day": 1, "hour": 0}}]},
        )
    )
    assert li.photos == 2 and li.hours_set and li.open_24h
    shut = parse_listing(
        _place(
            "p4",
            "Nine To Five Plumbing",
            regularOpeningHours={
                "periods": [{"open": {"day": 1, "hour": 9}, "close": {"day": 1, "hour": 17}}]
            },
        )
    )
    assert shut.hours_set and not shut.open_24h and shut.photos == 0
    assert not parse_listing(_place("p5", "No Hours")).hours_set


def test_the_nearby_search_asks_for_the_trade_and_drops_the_business_itself() -> None:
    mine = parse_listing(
        _place("mine", "Alpha Plumbing", primaryTypeDisplayName={"text": "Plumber"}),
    )
    mine = type(mine)(**{**mine.__dict__, "lat": 43.58, "lng": -79.64})
    sent: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        sent.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "places": [
                    _place("mine", "Alpha Plumbing"),
                    _place("r1", "Northgate Plumbing"),
                    _place("r2", "Lakeshore Drain Co"),
                ]
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        rivals = nearby_rivals(mine, api_key="k", limit=5, client=client)

    assert [r.place_id for r in rivals] == ["r1", "r2"]
    assert sent["textQuery"] == "Plumber"
    assert sent["locationBias"]["circle"]["radius"] == 15000.0


def test_nothing_nearby_without_a_point_on_the_map() -> None:
    bare = parse_listing(_place("x", "Somebody"))
    assert nearby_rivals(bare, api_key="k") == []


def test_the_town_is_geocoded_once_however_many_times_it_is_searched() -> None:
    """Typing calls this per keystroke; the town must not be looked up each time."""
    from ppcway.audit import places

    places._TOWNS.clear()
    calls = {"geocode": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url).startswith(GEOCODE_ENDPOINT):
            calls["geocode"] += 1
            return httpx.Response(200, json=MISSISSAUGA)
        return httpx.Response(200, json={"places": [_place("p1", "Alpha Plumbing")]})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        for typed in ["alp", "alph", "alpha"]:
            find_businesses(typed, api_key="k", city="Mississauga", client=client)

    assert calls["geocode"] == 1
    places._TOWNS.clear()
