"""Reading an account into the mirror, and noticing what changed without us.

Four passes, each one a GAQL read and an upsert:

  structure   campaigns, ad groups, keywords and ads, as they stand now
  today       this day's numbers, re-read through the day
  backfill    the previous three days, because conversions arrive late
  first       structure and ninety days, which is what a new account gets

The upsert is the whole point. A thing is matched on Google's own resource
name, its tracked fields are hashed, and the hash is compared with the one we
stored. Equal means nothing happened. Different means somebody changed it in
Google Ads, which is written down as an `ExternalChange` in plain words and
never silently overwritten.

Like the rest of the reads here, a refusal is an answer rather than an
exception: a pass that cannot read keywords still mirrors the campaigns, and
says what it could not read.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from ppcway.ads.accounts import API, _headers, _plain, _why
from ppcway.ads.mirror import (
    MICRO,
    CampaignDay,
    ExternalChange,
    KeywordDay,
    MirrorAd,
    MirrorAdGroup,
    MirrorCampaign,
    MirrorKeyword,
    SearchTermDay,
    SyncRun,
    fingerprint,
    term_key,
)

log = logging.getLogger(__name__)

CALL_KINDS = {"PHONE_CALL_LEAD", "CALL"}

#: How a changed field reads to somebody who did not change it. The second item
#: says how to show the value: money, or just itself.
WORDS: dict[str, tuple[str, str]] = {
    "budget_micros": ("Daily budget", "money"),
    "cpc_bid_micros": ("Bid", "money"),
    "status": ("Status", "plain"),
    "name": ("Name", "plain"),
    "text": ("Keyword", "plain"),
    "match_type": ("Match type", "plain"),
    "approval": ("Google's approval", "plain"),
    "bidding": ("Bidding strategy", "plain"),
    "headlines": ("Headlines", "list"),
    "descriptions": ("Descriptions", "list"),
    "final_urls": ("Landing page", "list"),
    "quality_score": ("Quality Score", "plain"),
    "negative": ("Negative", "plain"),
    "channel": ("Campaign type", "plain"),
    "starts_at": ("Start date", "plain"),
    "ends_at": ("End date", "plain"),
}


@dataclass
class Report:
    """What one pass did, in the words the screen and the gate both need."""

    ok: bool = True
    trouble: str = ""
    counts: dict[str, int] = field(default_factory=dict)
    #: One line per change somebody made in Google Ads since we last looked.
    changes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "trouble": self.trouble,
            "counts": self.counts,
            "changes": self.changes,
        }


def _ask(
    customer_id: str,
    query: str,
    *,
    access_token: str,
    developer_token: str,
    login_customer_id: str | None,
    api_version: str,
    client: httpx.Client,
) -> tuple[list[dict[str, Any]], str]:
    """Every row of one query, following Google's paging to the end."""
    rows: list[dict[str, Any]] = []
    body: dict[str, Any] = {"query": " ".join(query.split())}
    for _ in range(40):
        reply = client.post(
            f"{API}/{api_version}/customers/{customer_id}/googleAds:search",
            headers=_headers(access_token, developer_token, login_customer_id),
            json=body,
        )
        if reply.status_code != 200:
            log.warning("sync refused for %s: %s", customer_id, _why(reply))
            return [], _plain(reply)
        answer = reply.json()
        rows.extend(answer.get("results", []))
        token = answer.get("nextPageToken")
        if not token:
            break
        body["pageToken"] = token
    return rows, ""


def _share(value: Any) -> float | None:
    """One impression-share figure, or None where Google did not report one.

    Google sends these as a fraction between 0 and 1, and caps anything above
    0.9 at 0.9 for competitive reasons -- so a 0.9 here means "90% or better"
    and nothing may present it as exact. See `CampaignDay.share_is_capped`.
    """
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _money(micros: Any, currency: str) -> str:
    try:
        return f"{int(micros) / MICRO:,.2f} {currency}".strip()
    except (TypeError, ValueError):
        return "nothing"


def _describe(fields: dict[str, Any], before: dict[str, Any], currency: str) -> list[str]:
    """What changed, one plain line each, skipping what nobody would call news."""
    lines: list[str] = []
    for key, now in fields.items():
        was = before.get(key)
        if was == now:
            continue
        label, how = WORDS.get(key, (key.replace("_", " ").capitalize(), "plain"))
        if how == "money":
            lines.append(f"{label} changed from {_money(was, currency)} to {_money(now, currency)}")
        elif how == "list":
            lines.append(f"{label} changed")
        elif key == "status":
            lines.append(f"{str(now).capitalize()} in Google Ads, from {str(was).lower()}")
        else:
            lines.append(f"{label} changed from “{was}” to “{now}”")
    return lines


def _upsert(
    session: Session,
    model: type[Any],
    kind: str,
    customer_id: str,
    seen: dict[str, dict[str, Any]],
    *,
    labels: dict[str, str],
    currency: str,
    now: datetime,
) -> tuple[int, list[str]]:
    """Put one kind of thing into the mirror, and record what moved.

    `seen` is Google's answer keyed by resource name; its values are the tracked
    fields only. Anything we hold and Google no longer returns is marked gone
    rather than deleted, so yesterday is still comparable with today.
    """
    held = {
        row.resource_name: row
        for row in session.scalars(select(model).where(model.customer_id == customer_id))
    }
    changes: list[str] = []

    for resource_name, fields in seen.items():
        mark = fingerprint(fields)
        row = held.get(resource_name)
        if row is None:
            session.add(
                model(
                    customer_id=customer_id,
                    resource_name=resource_name,
                    fingerprint=mark,
                    seen_at=now,
                    changed_at=now,
                    **fields,
                )
            )
            continue
        row.seen_at = now
        row.gone_at = None
        if row.fingerprint == mark:
            continue
        before = {key: getattr(row, key) for key in fields}
        lines = _describe(fields, before, currency)
        # Nothing PPCway writes yet, so a moved fingerprint is somebody's own
        # hand in Google Ads. When PPCway can write it will stamp the row first,
        # and this is where the two have to be reconciled rather than guessed.
        if lines and row.source == "google":
            label = labels.get(resource_name, "")
            for line in lines:
                session.add(
                    ExternalChange(
                        customer_id=customer_id,
                        kind=kind,
                        resource_name=resource_name,
                        campaign_id=str(fields.get("campaign_id", "")),
                        label=label,
                        summary=line,
                        before={k: before.get(k) for k in fields},
                        after=dict(fields),
                        noticed_at=now,
                    )
                )
                changes.append(f"{label}: {line}" if label else line)
        for key, value in fields.items():
            setattr(row, key, value)
        row.fingerprint = mark
        row.changed_at = now

    for resource_name, row in held.items():
        if resource_name not in seen and row.gone_at is None:
            row.gone_at = now
            # The thing is gone from Google's answer, so this time its name has
            # to come from what we hold rather than from what was returned.
            name = getattr(row, "name", "") or getattr(row, "text", "") or resource_name
            said = f"{name} is no longer in the account"
            changes.append(said)
            # Deleting something is a change made in Google Ads like any other,
            # and the one a person is most likely to come looking for.
            session.add(
                ExternalChange(
                    customer_id=customer_id,
                    kind=kind,
                    resource_name=resource_name,
                    campaign_id=str(getattr(row, "campaign_id", "") or ""),
                    label=name,
                    summary=said,
                    before={"gone": False},
                    after={"gone": True},
                    noticed_at=now,
                )
            )

    return len(seen), changes


def sync_structure(
    session: Session,
    customer_id: str,
    *,
    access_token: str,
    developer_token: str,
    login_customer_id: str | None = None,
    api_version: str = "v25",
    client: httpx.Client | None = None,
    now: datetime | None = None,
) -> Report:
    """Campaigns, ad groups, keywords and ads, as the account stands now."""
    own = client is None
    c = client or httpx.Client(timeout=httpx.Timeout(90))
    at = now or datetime.now(UTC)
    report = Report()
    ask = {
        "access_token": access_token,
        "developer_token": developer_token,
        "login_customer_id": login_customer_id,
        "api_version": api_version,
        "client": c,
    }
    try:
        rows, trouble = _ask(
            customer_id,
            """
            SELECT campaign.resource_name, campaign.id, campaign.name, campaign.status,
                   campaign.advertising_channel_type, campaign.bidding_strategy_type,
                   campaign.start_date_time, campaign.end_date_time,
                   campaign_budget.amount_micros, customer.currency_code
            FROM campaign WHERE campaign.status != 'REMOVED'
            """,
            **ask,  # type: ignore[arg-type]
        )
        if trouble:
            return Report(ok=False, trouble=trouble)

        currency = ""
        campaigns: dict[str, dict[str, Any]] = {}
        labels: dict[str, str] = {}
        for row in rows:
            campaign = row.get("campaign", {})
            name = str(campaign.get("resourceName", ""))
            if not name:
                continue
            currency = currency or str(row.get("customer", {}).get("currencyCode", ""))
            labels[name] = str(campaign.get("name", ""))
            campaigns[name] = {
                "campaign_id": str(campaign.get("id", "")),
                "name": str(campaign.get("name", "")),
                "status": str(campaign.get("status", "")),
                "channel": str(campaign.get("advertisingChannelType", "")),
                "bidding": str(campaign.get("biddingStrategyType", "")),
                "budget_micros": int(row.get("campaignBudget", {}).get("amountMicros", 0) or 0),
                "starts_at": str(campaign.get("startDateTime", "")),
                "ends_at": str(campaign.get("endDateTime", "")),
            }
        count, changes = _upsert(
            session,
            MirrorCampaign,
            "campaign",
            customer_id,
            campaigns,
            labels=labels,
            currency=currency,
            now=at,
        )
        report.counts["campaigns"] = count
        report.changes.extend(changes)

        rows, trouble = _ask(
            customer_id,
            """
            SELECT ad_group.resource_name, ad_group.id, ad_group.name, ad_group.status,
                   ad_group.cpc_bid_micros, campaign.id
            FROM ad_group WHERE ad_group.status != 'REMOVED'
            """,
            **ask,  # type: ignore[arg-type]
        )
        if trouble:
            report.trouble = trouble
        else:
            groups: dict[str, dict[str, Any]] = {}
            labels = {}
            for row in rows:
                group = row.get("adGroup", {})
                name = str(group.get("resourceName", ""))
                if not name:
                    continue
                labels[name] = str(group.get("name", ""))
                groups[name] = {
                    "ad_group_id": str(group.get("id", "")),
                    "campaign_id": str(row.get("campaign", {}).get("id", "")),
                    "name": str(group.get("name", "")),
                    "status": str(group.get("status", "")),
                    "cpc_bid_micros": int(group.get("cpcBidMicros", 0) or 0),
                }
            count, changes = _upsert(
                session,
                MirrorAdGroup,
                "ad_group",
                customer_id,
                groups,
                labels=labels,
                currency=currency,
                now=at,
            )
            report.counts["ad_groups"] = count
            report.changes.extend(changes)

        rows, trouble = _ask(
            customer_id,
            """
            SELECT ad_group_criterion.resource_name, ad_group_criterion.criterion_id,
                   ad_group_criterion.keyword.text, ad_group_criterion.keyword.match_type,
                   ad_group_criterion.status, ad_group_criterion.negative,
                   ad_group_criterion.quality_info.quality_score,
                   ad_group_criterion.cpc_bid_micros, ad_group.id, campaign.id
            FROM ad_group_criterion
            WHERE ad_group_criterion.type = 'KEYWORD'
              AND ad_group_criterion.status != 'REMOVED'
            """,
            **ask,  # type: ignore[arg-type]
        )
        if trouble:
            report.trouble = report.trouble or trouble
        else:
            keywords: dict[str, dict[str, Any]] = {}
            labels = {}
            for row in rows:
                criterion = row.get("adGroupCriterion", {})
                name = str(criterion.get("resourceName", ""))
                if not name:
                    continue
                word = criterion.get("keyword", {})
                labels[name] = str(word.get("text", ""))
                keywords[name] = {
                    "criterion_id": str(criterion.get("criterionId", "")),
                    "ad_group_id": str(row.get("adGroup", {}).get("id", "")),
                    "campaign_id": str(row.get("campaign", {}).get("id", "")),
                    "text": str(word.get("text", "")),
                    "match_type": str(word.get("matchType", "")),
                    "status": str(criterion.get("status", "")),
                    "negative": bool(criterion.get("negative", False)),
                    "quality_score": int(
                        criterion.get("qualityInfo", {}).get("qualityScore", 0) or 0
                    ),
                    "cpc_bid_micros": int(criterion.get("cpcBidMicros", 0) or 0),
                }
            count, changes = _upsert(
                session,
                MirrorKeyword,
                "keyword",
                customer_id,
                keywords,
                labels=labels,
                currency=currency,
                now=at,
            )
            report.counts["keywords"] = count
            report.changes.extend(changes)

        rows, trouble = _ask(
            customer_id,
            """
            SELECT ad_group_ad.resource_name, ad_group_ad.ad.id, ad_group_ad.ad.type,
                   ad_group_ad.ad.responsive_search_ad.headlines,
                   ad_group_ad.ad.responsive_search_ad.descriptions,
                   ad_group_ad.ad.final_urls, ad_group_ad.status,
                   ad_group_ad.policy_summary.approval_status, ad_group.id, campaign.id
            FROM ad_group_ad WHERE ad_group_ad.status != 'REMOVED'
            """,
            **ask,  # type: ignore[arg-type]
        )
        if trouble:
            report.trouble = report.trouble or trouble
        else:
            ads: dict[str, dict[str, Any]] = {}
            labels = {}
            for row in rows:
                entry = row.get("adGroupAd", {})
                name = str(entry.get("resourceName", ""))
                if not name:
                    continue
                ad = entry.get("ad", {})
                search_ad = ad.get("responsiveSearchAd", {})
                headlines = [str(h.get("text", "")) for h in search_ad.get("headlines", [])]
                labels[name] = " · ".join(headlines[:2]) or str(ad.get("id", ""))
                ads[name] = {
                    "ad_id": str(ad.get("id", "")),
                    "ad_group_id": str(row.get("adGroup", {}).get("id", "")),
                    "campaign_id": str(row.get("campaign", {}).get("id", "")),
                    "kind": str(ad.get("type", "")),
                    "status": str(entry.get("status", "")),
                    "approval": str(entry.get("policySummary", {}).get("approvalStatus", "")),
                    "headlines": headlines,
                    "descriptions": [
                        str(d.get("text", "")) for d in search_ad.get("descriptions", [])
                    ],
                    "final_urls": [str(u) for u in ad.get("finalUrls", [])],
                }
            count, changes = _upsert(
                session,
                MirrorAd,
                "ad",
                customer_id,
                ads,
                labels=labels,
                currency=currency,
                now=at,
            )
            report.counts["ads"] = count
            report.changes.extend(changes)

        session.commit()
        return report
    finally:
        if own:
            c.close()


def sync_days(
    session: Session,
    customer_id: str,
    *,
    since: date,
    until: date | None = None,
    access_token: str,
    developer_token: str,
    login_customer_id: str | None = None,
    api_version: str = "v25",
    client: httpx.Client | None = None,
    now: datetime | None = None,
) -> Report:
    """One row per campaign per day, rewritten every time it is read.

    Two queries, because Google refuses to report the conversion category beside
    clicks, cost or impressions. The money comes by day and the calls-and-forms
    split beside it, merged on the campaign and the date.
    """
    own = client is None
    c = client or httpx.Client(timeout=httpx.Timeout(90))
    at = now or datetime.now(UTC)
    last = until or at.date()
    report = Report()
    ask = {
        "access_token": access_token,
        "developer_token": developer_token,
        "login_customer_id": login_customer_id,
        "api_version": api_version,
        "client": c,
    }
    window = f"segments.date BETWEEN '{since.isoformat()}' AND '{last.isoformat()}'"
    try:
        rows, trouble = _ask(
            customer_id,
            f"""
            SELECT campaign.id, segments.date, metrics.impressions, metrics.clicks,
                   metrics.cost_micros, metrics.conversions, metrics.conversions_value,
                   metrics.search_impression_share,
                   metrics.search_budget_lost_impression_share,
                   metrics.search_rank_lost_impression_share,
                   metrics.search_absolute_top_impression_share
            FROM campaign WHERE {window}
            """,
            **ask,  # type: ignore[arg-type]
        )
        if trouble:
            return Report(ok=False, trouble=trouble)

        facts: dict[tuple[str, str], dict[str, Any]] = {}
        for row in rows:
            campaign_id = str(row.get("campaign", {}).get("id", ""))
            day = str(row.get("segments", {}).get("date", ""))
            if not campaign_id or not day:
                continue
            metrics = row.get("metrics", {})
            facts[(campaign_id, day)] = {
                "impressions": int(metrics.get("impressions", 0) or 0),
                "clicks": int(metrics.get("clicks", 0) or 0),
                "cost_micros": int(metrics.get("costMicros", 0) or 0),
                "conversions": float(metrics.get("conversions", 0) or 0),
                "conversion_value_micros": round(
                    float(metrics.get("conversionsValue", 0) or 0) * MICRO
                ),
                "calls": 0.0,
                "forms": 0.0,
                # None rather than 0.0 where Google did not report it. A
                # campaign that is not a Search campaign has no search
                # impression share at all, and zero would read as "you were in
                # none of the auctions" -- a far more alarming claim than
                # "Google did not say". `_share` keeps the distinction.
                "search_share": _share(metrics.get("searchImpressionShare")),
                "lost_to_budget": _share(metrics.get("searchBudgetLostImpressionShare")),
                "lost_to_rank": _share(metrics.get("searchRankLostImpressionShare")),
                "top_share": _share(metrics.get("searchAbsoluteTopImpressionShare")),
            }

        split, trouble = _ask(
            customer_id,
            f"""
            SELECT campaign.id, segments.date, segments.conversion_action_category,
                   metrics.conversions
            FROM campaign WHERE {window}
            """,
            **ask,  # type: ignore[arg-type]
        )
        if trouble:
            report.trouble = trouble
        for row in split:
            campaign_id = str(row.get("campaign", {}).get("id", ""))
            day = str(row.get("segments", {}).get("date", ""))
            fact = facts.get((campaign_id, day))
            if fact is None:
                continue
            kind = str(row.get("segments", {}).get("conversionActionCategory", ""))
            amount = float(row.get("metrics", {}).get("conversions", 0) or 0)
            if kind in CALL_KINDS:
                fact["calls"] += amount
            else:
                fact["forms"] += amount

        held = {
            (kept.campaign_id, kept.day.isoformat()): kept
            for kept in session.scalars(
                select(CampaignDay).where(
                    CampaignDay.customer_id == customer_id,
                    CampaignDay.day >= since,
                    CampaignDay.day <= last,
                )
            )
        }
        for (campaign_id, day), fact in facts.items():
            kept = held.get((campaign_id, day))
            if kept is None:
                session.add(
                    CampaignDay(
                        customer_id=customer_id,
                        campaign_id=campaign_id,
                        day=date.fromisoformat(day),
                        refreshed_at=at,
                        **fact,
                    )
                )
                continue
            for key, value in fact.items():
                setattr(kept, key, value)
            kept.refreshed_at = at

        report.counts["days"] = len({day for _, day in facts})
        report.counts["rows"] = len(facts)
        session.commit()
        return report
    finally:
        if own:
            c.close()


def sync_search_terms(
    session: Session,
    customer_id: str,
    *,
    since: date,
    until: date | None = None,
    access_token: str,
    developer_token: str,
    login_customer_id: str | None = None,
    api_version: str = "v25",
    client: httpx.Client | None = None,
    now: datetime | None = None,
) -> Report:
    """What people actually typed, per day, and whether it is already handled.

    One query. `search_term_view` is the only place Google reports the words a
    person really searched for, and `status` beside them is what keeps rule R1
    from proposing an exclusion for a term already excluded -- the fastest way
    to lose a merchant's trust is to recommend something they have already done.

    Rows with no impressions are skipped rather than stored. Google reports a
    row for a term that merely matched, and a table of nothing-happened is most
    of the storage and none of the signal.
    """
    own = client is None
    c = client or httpx.Client(timeout=httpx.Timeout(90))
    at = now or datetime.now(UTC)
    last = until or at.date()
    report = Report()
    window = f"segments.date BETWEEN '{since.isoformat()}' AND '{last.isoformat()}'"
    try:
        rows, trouble = _ask(
            customer_id,
            f"""
            SELECT search_term_view.search_term, search_term_view.status,
                   segments.date, campaign.id, ad_group.id, segments.keyword.info.text,
                   metrics.impressions, metrics.clicks, metrics.cost_micros,
                   metrics.conversions, metrics.conversions_value
            FROM search_term_view WHERE {window}
            """,
            access_token=access_token,
            developer_token=developer_token,
            login_customer_id=login_customer_id,
            api_version=api_version,
            client=c,
        )
        if trouble:
            return Report(ok=False, trouble=trouble)

        facts: dict[tuple[str, str, str], dict[str, Any]] = {}
        for row in rows:
            view = row.get("searchTermView", {})
            term = str(view.get("searchTerm", "") or "")
            day = str(row.get("segments", {}).get("date", ""))
            ad_group_id = str(row.get("adGroup", {}).get("id", "") or "")
            if not term or not day:
                continue
            metrics = row.get("metrics", {})
            impressions = int(metrics.get("impressions", 0) or 0)
            if impressions <= 0:
                continue
            keyword = row.get("segments", {}).get("keyword", {}).get("info", {})
            facts[(ad_group_id, term_key(term), day)] = {
                "campaign_id": str(row.get("campaign", {}).get("id", "") or ""),
                "ad_group_id": ad_group_id,
                "term": term[:1000],
                "status": str(view.get("status", "") or ""),
                "matched_keyword": str(keyword.get("text", "") or "")[:255],
                "impressions": impressions,
                "clicks": int(metrics.get("clicks", 0) or 0),
                "cost_micros": int(metrics.get("costMicros", 0) or 0),
                "conversions": float(metrics.get("conversions", 0) or 0),
                "conversion_value_micros": round(
                    float(metrics.get("conversionsValue", 0) or 0) * MICRO
                ),
            }

        held = {
            (kept.ad_group_id, kept.term_hash, kept.day.isoformat()): kept
            for kept in session.scalars(
                select(SearchTermDay).where(
                    SearchTermDay.customer_id == customer_id,
                    SearchTermDay.day >= since,
                    SearchTermDay.day <= last,
                )
            )
        }
        for (ad_group_id, hashed, day), fact in facts.items():
            kept = held.get((ad_group_id, hashed, day))
            if kept is None:
                session.add(
                    SearchTermDay(
                        customer_id=customer_id,
                        term_hash=hashed,
                        day=date.fromisoformat(day),
                        refreshed_at=at,
                        **fact,
                    )
                )
                continue
            for key, value in fact.items():
                setattr(kept, key, value)
            kept.refreshed_at = at

        report.counts["search_terms"] = len({hashed for _, hashed, _ in facts})
        report.counts["rows"] = len(facts)
        session.commit()
        return report
    finally:
        if own:
            c.close()


def sync_keyword_days(
    session: Session,
    customer_id: str,
    *,
    since: date,
    until: date | None = None,
    access_token: str,
    developer_token: str,
    login_customer_id: str | None = None,
    api_version: str = "v25",
    client: httpx.Client | None = None,
    now: datetime | None = None,
) -> Report:
    """One keyword, one day. What the guardrails need to call something a loser.

    "A keyword has spent 1.5 times the target cost per lead, or taken 100
    clicks, and brought nothing back" is a question about one keyword over a
    window, and the structure mirror cannot answer it: that holds what a
    keyword is, not what it did.

    Quality Score is not read here. Google reports it as a property of the
    keyword now rather than as a figure for a past day, so it stays on the
    structure mirror; writing it onto each day's row would invent a history
    Google never gave us.
    """
    own = client is None
    c = client or httpx.Client(timeout=httpx.Timeout(90))
    at = now or datetime.now(UTC)
    last = until or at.date()
    report = Report()
    window = f"segments.date BETWEEN '{since.isoformat()}' AND '{last.isoformat()}'"
    try:
        rows, trouble = _ask(
            customer_id,
            f"""
            SELECT ad_group_criterion.criterion_id, ad_group_criterion.keyword.text,
                   ad_group_criterion.keyword.match_type, ad_group.id, campaign.id,
                   segments.date, metrics.impressions, metrics.clicks,
                   metrics.cost_micros, metrics.conversions, metrics.conversions_value
            FROM keyword_view WHERE {window}
            """,
            access_token=access_token,
            developer_token=developer_token,
            login_customer_id=login_customer_id,
            api_version=api_version,
            client=c,
        )
        if trouble:
            return Report(ok=False, trouble=trouble)

        facts: dict[tuple[str, str], dict[str, Any]] = {}
        for row in rows:
            criterion = row.get("adGroupCriterion", {})
            criterion_id = str(criterion.get("criterionId", "") or "")
            day = str(row.get("segments", {}).get("date", ""))
            if not criterion_id or not day:
                continue
            metrics = row.get("metrics", {})
            if int(metrics.get("impressions", 0) or 0) <= 0:
                continue
            keyword = criterion.get("keyword", {})
            facts[(criterion_id, day)] = {
                "ad_group_id": str(row.get("adGroup", {}).get("id", "") or ""),
                "campaign_id": str(row.get("campaign", {}).get("id", "") or ""),
                "text": str(keyword.get("text", "") or "")[:255],
                "match_type": str(keyword.get("matchType", "") or ""),
                "impressions": int(metrics.get("impressions", 0) or 0),
                "clicks": int(metrics.get("clicks", 0) or 0),
                "cost_micros": int(metrics.get("costMicros", 0) or 0),
                "conversions": float(metrics.get("conversions", 0) or 0),
                "conversion_value_micros": round(
                    float(metrics.get("conversionsValue", 0) or 0) * MICRO
                ),
            }

        held = {
            (kept.criterion_id, kept.day.isoformat()): kept
            for kept in session.scalars(
                select(KeywordDay).where(
                    KeywordDay.customer_id == customer_id,
                    KeywordDay.day >= since,
                    KeywordDay.day <= last,
                )
            )
        }
        for (criterion_id, day), fact in facts.items():
            kept = held.get((criterion_id, day))
            if kept is None:
                session.add(
                    KeywordDay(
                        customer_id=customer_id,
                        criterion_id=criterion_id,
                        day=date.fromisoformat(day),
                        refreshed_at=at,
                        **fact,
                    )
                )
                continue
            for key, value in fact.items():
                setattr(kept, key, value)
            kept.refreshed_at = at

        report.counts["keywords"] = len({criterion for criterion, _ in facts})
        report.counts["rows"] = len(facts)
        session.commit()
        return report
    finally:
        if own:
            c.close()


def backfill_since(today: date, days: int = 3) -> date:
    """The first day the nightly pass re-reads: conversions arrive late."""
    return today - timedelta(days=days)


def record(session: Session, customer_id: str, kind: str, stage: str = "") -> SyncRun:
    """Open a run, so a screen has something to show while it happens."""
    run = SyncRun(customer_id=customer_id, kind=kind, status="running", stage=stage)
    session.add(run)
    session.commit()
    return run


def finish(session: Session, run: SyncRun, report: Report, now: datetime | None = None) -> SyncRun:
    """Close a run with what it found, for the screen and for the gate."""
    run.status = "done" if report.ok and not report.trouble else "failed"
    run.counts = {**report.counts, "changes": len(report.changes)}
    run.trouble = report.trouble
    run.stage = ""
    run.finished_at = now or datetime.now(UTC)
    session.commit()
    return run
