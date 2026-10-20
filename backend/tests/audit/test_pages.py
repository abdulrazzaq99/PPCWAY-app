"""Every page the ads send people to, judged.

The value here is not the checking, it is where the list comes from: the mirror
knows which pages Google is sending paid traffic to, so this is never a guess
about which pages matter.
"""

from __future__ import annotations

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session as DbSession

from ppcway.ads.mirror import MirrorAd, MirrorCampaign
from ppcway.audit.pages import check_pages, judge, landing_pages, tidy
from ppcway.audit.render import Rendering
from ppcway.config import Settings
from ppcway.db.base import Base


@pytest.fixture
def db() -> DbSession:
    engine = sa.create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with DbSession(engine) as session:
        yield session


def campaign(db: DbSession, campaign_id: str, name: str) -> None:
    db.add(
        MirrorCampaign(
            customer_id="1",
            resource_name=f"customers/1/campaigns/{campaign_id}",
            campaign_id=campaign_id,
            name=name,
            status="ENABLED",
        )
    )
    db.commit()


def ad(db: DbSession, ad_id: str, campaign_id: str, urls: list[str], gone: bool = False) -> None:
    from datetime import UTC, datetime

    db.add(
        MirrorAd(
            customer_id="1",
            resource_name=f"customers/1/adGroupAds/21~{ad_id}",
            ad_id=ad_id,
            ad_group_id="21",
            campaign_id=campaign_id,
            status="ENABLED",
            approval="APPROVED",
            headlines=["A headline"],
            final_urls=urls,
            gone_at=datetime(2026, 10, 1, tzinfo=UTC) if gone else None,
        )
    )
    db.commit()


def page(**over: object) -> Rendering:
    """A page with nothing wrong with it, before a test spoils one thing."""
    fields: dict[str, object] = {
        "url": "https://alphaplumbing.ca/emergency",
        "final_url": "https://alphaplumbing.ca/emergency",
        "title": "Emergency plumber in Mississauga",
        "html": "<html><body><form></form></body></html>",
        "headline": "24 hour emergency plumber",
        "has_h1": True,
        "phone_above_fold": True,
        "tel_links": ["tel:+19055550199"],
        "viewport_meta": True,
        "overflow_x": False,
        "requests": ["https://googleads.g.doubleclick.net/pagead/viewthroughconversion/123"],
        "scripts": ["https://www.googletagmanager.com/gtag/js?id=AW-123456789"],
        "data_layer": [],
    }
    fields.update(over)
    return Rendering(**fields)  # type: ignore[arg-type]


def test_the_pages_come_from_the_ads_themselves(db: DbSession) -> None:
    campaign(db, "11", "Emergency plumbing")
    campaign(db, "12", "Drain cleaning")
    ad(db, "41", "11", ["https://alphaplumbing.ca/emergency?utm_source=google"])
    ad(db, "42", "12", ["https://alphaplumbing.ca/emergency"])
    ad(db, "43", "12", ["https://alphaplumbing.ca/drains/"])

    found = landing_pages(db, "1")

    # One entry a page: tracking parameters and a trailing slash are not a
    # different page, and both campaigns that send people there are named.
    assert set(found) == {
        "https://alphaplumbing.ca/emergency",
        "https://alphaplumbing.ca/drains",
    }
    assert found["https://alphaplumbing.ca/emergency"] == ["Emergency plumbing", "Drain cleaning"]


def test_an_ad_no_longer_running_does_not_bring_its_page(db: DbSession) -> None:
    campaign(db, "11", "Emergency plumbing")
    ad(db, "41", "11", ["https://alphaplumbing.ca/old-offer"], gone=True)

    assert landing_pages(db, "1") == {}


def test_tidy_refuses_something_that_is_not_an_address() -> None:
    assert tidy("not a url") == ""
    assert tidy("  https://Alpha.CA/Path/  ") == "https://alpha.ca/Path"


def test_a_page_with_everything_in_place_has_nothing_to_say() -> None:
    check = judge(page(), "https://alphaplumbing.ca/emergency", ["Emergency plumbing"])

    assert check.ok is True
    assert check.jobs == []
    assert check.conversion_tag is True
    assert check.tag_fired is True


def test_a_page_with_no_conversion_tag_is_the_first_thing_said() -> None:
    check = judge(
        page(requests=[], scripts=[], html="<html><form></form></html>"),
        "https://alphaplumbing.ca/emergency",
        [],
    )

    assert check.conversion_tag is False
    assert "invisible in your advertising" in check.jobs[0]


def test_a_tag_that_is_there_but_never_fired_is_said_differently() -> None:
    check = judge(
        page(requests=["https://www.googletagmanager.com/gtag/js?id=AW-123456789"]),
        "https://alphaplumbing.ca/emergency",
        [],
    )

    assert check.conversion_tag is True
    assert check.tag_fired is False
    assert "sent nothing when the page opened" in check.jobs[0]


def test_a_phone_number_below_the_fold_is_worth_saying() -> None:
    check = judge(page(phone_above_fold=False), "https://alphaplumbing.ca/emergency", [])

    assert any("not visible until you scroll" in job for job in check.jobs)


def test_a_pop_up_over_the_page_is_quoted_back() -> None:
    check = judge(
        page(overlay="Join our newsletter for 10% off"),
        "https://alphaplumbing.ca/emergency",
        [],
    )

    assert any("Join our newsletter" in job for job in check.jobs)


def test_a_page_that_does_not_fit_a_phone_is_said_in_those_words() -> None:
    check = judge(page(overflow_x=True), "https://alphaplumbing.ca/emergency", [])

    assert any("sideways" in job for job in check.jobs)


def test_a_page_that_will_not_open_is_the_worst_finding_of_all() -> None:
    def broken(url: str, **kwargs: object) -> Rendering:
        raise RuntimeError("the browser gave up")

    checked = check_pages(
        {"https://alphaplumbing.ca/gone": ["Emergency plumbing"]},
        Settings(),
        render_page=broken,
    )

    assert checked[0].read is False
    assert "every click that lands here is wasted" in checked[0].jobs[0]
    assert checked[0].campaigns == ["Emergency plumbing"]


def test_only_so_many_pages_are_opened() -> None:
    opened: list[str] = []

    def draw(url: str, **kwargs: object) -> Rendering:
        opened.append(url)
        return page(url=url, final_url=url)

    pages = {f"https://alphaplumbing.ca/{n}": [] for n in range(12)}
    check_pages(pages, Settings(), most=3, render_page=draw)

    assert len(opened) == 3
