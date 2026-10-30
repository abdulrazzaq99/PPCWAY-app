"""What a connected Google Ads account already tells us about its business.

The point of this module is that the audit stops asking for a name and a
website it was handed when the account was connected — and, just as much, that
it never quietly pairs one business's website with another's spending.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session, sessionmaker

from ppcway.ads import business as module
from ppcway.ads.business import host_of, known_business, site_from_ads
from ppcway.ads.mirror import MirrorAd
from ppcway.audit.places import Listing
from ppcway.db.base import Base
from ppcway.org.places import home_for

CUSTOMER = "2580586343"


def listing(
    *, place_id: str, name: str, website: str, address: str = "12 King St, Mississauga"
) -> Listing:
    return Listing(
        place_id=place_id,
        name=name,
        address=f"{address}, ON L5B 1M2, Canada",
        short_address=address,
        category="Plumber",
        status="OPERATIONAL",
        service_area_only=False,
        maps_url="",
        rating=4.6,
        reviews=120,
        website=website,
        phone="",
        open_now=None,
        lat=None,
        lng=None,
    )


@pytest.fixture
def db() -> Iterator[sessionmaker[Session]]:
    engine = sa.create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=sa.pool.StaticPool
    )
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, expire_on_commit=False, future=True)
    Base.metadata.drop_all(engine)


def an_ad(session: Session, ad_id: str, urls: list[str], *, gone: bool = False) -> None:
    session.add(
        MirrorAd(
            customer_id=CUSTOMER,
            resource_name=f"customers/{CUSTOMER}/adGroupAds/{ad_id}",
            ad_id=ad_id,
            ad_group_id="1",
            campaign_id="1",
            final_urls=urls,
            gone_at=sa.func.now() if gone else None,
        )
    )


def test_a_bare_host_is_what_we_compare_on() -> None:
    assert host_of("https://www.Alpha-Plumbing.ca/taps?utm=x") == "alpha-plumbing.ca"
    assert host_of("alphaplumbing.ca") == "alphaplumbing.ca"
    assert host_of("") == ""


def test_the_website_is_where_most_of_the_ads_point(db: sessionmaker[Session]) -> None:
    """An account can advertise two sites; the business is the one most ads use."""
    with db() as session:
        an_ad(session, "1", ["https://pdfezy.com/en/sign-pdf"])
        an_ad(session, "2", ["https://www.pdfezy.com/"])
        an_ad(session, "3", ["https://someothersite.ca/"])
        session.commit()
        assert site_from_ads(session, CUSTOMER) == "pdfezy.com"


def test_an_ad_that_is_gone_does_not_vote(db: sessionmaker[Session]) -> None:
    with db() as session:
        an_ad(session, "1", ["https://old-site.ca/"], gone=True)
        an_ad(session, "2", ["https://pdfezy.com/"])
        session.commit()
        assert site_from_ads(session, CUSTOMER) == "pdfezy.com"


def test_with_no_ads_yet_there_is_no_website(db: sessionmaker[Session]) -> None:
    with db() as session:
        assert site_from_ads(session, CUSTOMER) == ""
        known = known_business(session, customer_id=CUSTOMER, account_name="Byte9")
        assert known.site == ""
        assert known.enough is False


def test_a_listing_is_certain_only_when_its_website_is_the_one_being_advertised(
    db: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        module,
        "find_businesses",
        lambda name, **k: [
            listing(place_id="wrong", name="Alpha Plumbing Ltd", website="https://someoneelse.ca"),
            listing(place_id="right", name="Alpha Plumbing", website="https://alphaplumbing.ca"),
        ],
    )
    with db() as session:
        an_ad(session, "1", ["https://alphaplumbing.ca/emergency"])
        session.commit()

        known = known_business(
            session, customer_id=CUSTOMER, account_name="Alpha Plumbing", maps_key="k"
        )

    assert known.sure is True
    assert known.place_id == "right"
    assert known.site == "alphaplumbing.ca"
    assert known.city == "Mississauga"
    assert known.trade == "Plumber"
    assert known.whence["site"] == "the pages your ads send people to"
    assert known.choices == []


def test_when_no_listing_matches_the_website_it_asks_instead_of_guessing(
    db: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Picking the first listing by name is how one business gets another's audit."""
    monkeypatch.setattr(
        module,
        "find_businesses",
        lambda name, **k: [
            listing(place_id="a", name="Alpha Plumbing", website="https://notus.ca"),
            listing(place_id="b", name="Alpha Plumbing Inc", website=""),
        ],
    )
    with db() as session:
        an_ad(session, "1", ["https://alphaplumbing.ca/"])
        session.commit()

        known = known_business(
            session, customer_id=CUSTOMER, account_name="Alpha Plumbing", maps_key="k"
        )

    assert known.sure is False
    assert known.place_id == ""
    assert [one["place_id"] for one in known.choices] == ["a", "b"]
    # The audit can still run: the website and the name are not in doubt.
    assert known.enough is True


def test_without_a_maps_key_it_still_knows_the_name_and_the_website(
    db: sessionmaker[Session],
) -> None:
    with db() as session:
        an_ad(session, "1", ["https://pdfezy.com/"])
        session.commit()
        known = known_business(session, customer_id=CUSTOMER, account_name="pdfezy")
    assert (known.name, known.site, known.enough) == ("pdfezy", "pdfezy.com", True)
    assert known.place_id == ""


def test_an_account_with_no_name_is_called_after_its_website(db: sessionmaker[Session]) -> None:
    with db() as session:
        an_ad(session, "1", ["https://pdfezy.com/"])
        session.commit()
        known = known_business(session, customer_id=CUSTOMER, account_name="")
    assert known.name == "pdfezy"
    assert known.whence["name"] == "your website address"


def test_the_endpoint_answers_what_the_account_knows(monkeypatch: pytest.MonkeyPatch) -> None:
    """End to end: a connected account, and a screen that need ask nothing."""
    from cryptography.fernet import Fernet
    from fastapi.testclient import TestClient
    from pydantic import SecretStr

    from ppcway.ads import models as ads_models
    from ppcway.api.app import create_app
    from ppcway.auth import google
    from ppcway.auth.models import UserAccount
    from ppcway.config import Settings
    from ppcway.db.session import get_session

    key = Fernet.generate_key()
    engine = sa.create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=sa.pool.StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)

    monkeypatch.setattr(
        google.id_token,  # type: ignore[attr-defined]
        "verify_oauth2_token",
        lambda credential, *a, **k: {
            "sub": "google-dana",
            "email": "dana@alphaplumbing.ca",
            "email_verified": True,
            "name": "Dana",
        },
    )
    monkeypatch.setattr(
        module,
        "find_businesses",
        lambda name, **k: [
            listing(place_id="right", name="Alpha Plumbing", website="https://alphaplumbing.ca")
        ],
    )

    app = create_app(
        Settings(
            google_signin_client_id="test-client",
            google_oauth_token_key=SecretStr(key.decode()),
            google_maps_api_key=SecretStr("maps-key"),
        )
    )

    def one_session() -> Iterator[Session]:
        session = factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_session] = one_session
    try:
        with TestClient(app) as client:
            token = client.post("/v1/auth/google", json={"credential": "d" * 40}).json()["token"]
            with factory() as session:
                account = session.scalars(sa.select(UserAccount)).one()
                session.add(
                    ads_models.AdsConnection(
                        account_id=account.id,
                        organization_id=home_for(session, account).id,
                        ciphertext=Fernet(key).encrypt(b"a-permission").decode(),
                        customer_id=CUSTOMER,
                        customer_name="Alpha Plumbing",
                        currency="CAD",
                    )
                )
                an_ad(session, "1", ["https://alphaplumbing.ca/emergency"])
                session.commit()

            said = client.get("/v1/ads/business", headers={"x-session-token": token}).json()

        assert said["connected"] is True
        assert said["enough"] is True
        assert said["name"] == "Alpha Plumbing"
        assert said["site"] == "alphaplumbing.ca"
        assert said["place_id"] == "right"
        assert said["sure"] is True
        assert said["city"] == "Mississauga"
    finally:
        Base.metadata.drop_all(engine)


def test_the_endpoint_says_nothing_when_no_account_is_connected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from fastapi.testclient import TestClient

    from ppcway.api.app import create_app
    from ppcway.auth import google
    from ppcway.config import Settings
    from ppcway.db.session import get_session

    engine = sa.create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=sa.pool.StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    monkeypatch.setattr(
        google.id_token,  # type: ignore[attr-defined]
        "verify_oauth2_token",
        lambda credential, *a, **k: {
            "sub": "google-dana",
            "email": "dana@alphaplumbing.ca",
            "email_verified": True,
            "name": "Dana",
        },
    )
    app = create_app(Settings(google_signin_client_id="test-client"))

    def one_session() -> Iterator[Session]:
        session = factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_session] = one_session
    try:
        with TestClient(app) as client:
            token = client.post("/v1/auth/google", json={"credential": "d" * 40}).json()["token"]
            said = client.get("/v1/ads/business", headers={"x-session-token": token}).json()
        assert said == {"connected": False, "enough": False}
    finally:
        Base.metadata.drop_all(engine)


def test_with_no_website_in_the_ads_the_listing_can_supply_one(
    db: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A brand new account has no live ads, so Maps is where the website is."""
    monkeypatch.setattr(
        module,
        "find_businesses",
        lambda name, **k: [
            listing(place_id="a", name="Alpha Plumbing", website="https://alphaplumbing.ca")
        ],
    )
    with db() as session:
        known = known_business(
            session, customer_id=CUSTOMER, account_name="Alpha Plumbing", maps_key="k"
        )

    assert known.site == ""
    assert known.sure is False
    # Nothing is assumed, but there is something to offer rather than a blank form.
    assert known.enough is True
    assert known.choices[0]["website"] == "https://alphaplumbing.ca"


def test_signed_out_the_endpoint_refuses_and_the_free_audit_is_untouched() -> None:
    """The free audit asks for a business name because nobody has told us one.

    This flow is for somebody who has signed in and connected an account. With
    no session there is no account, nothing to read, and nothing to fill in, so
    the public form stays exactly as it was.
    """
    from fastapi.testclient import TestClient

    from ppcway.api.app import create_app
    from ppcway.config import Settings
    from ppcway.db.session import get_session

    engine = sa.create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=sa.pool.StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    app = create_app(Settings(google_signin_client_id="test-client"))

    def one_session() -> Iterator[Session]:
        session = factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_session] = one_session
    try:
        with TestClient(app) as client:
            assert client.get("/v1/ads/business").status_code == 401
            assert (
                client.get("/v1/ads/business", headers={"x-session-token": "made up"}).status_code
                == 401
            )
    finally:
        Base.metadata.drop_all(engine)
