"""The eight things Otto may look up, and the one thing it may not.

The client's brief names them, and the shape of this module is the scope
enforcement: **a tool never learns which account it is reading.** The customer
id, the organisation and the currency come from the signed-in session and are
put into `Asked` by the code that runs the tool; no schema below accepts an
account, a target or a figure, so there is nothing for a model to supply and
nothing for an injected instruction to redirect. The brief's rule -- *target
resolved server-side from a tool-returned id; never a model-supplied budget,
bid or target* -- is enforced by the schemas not having those fields rather
than by checking values the model sent.

Every tool reads the mirror, never Google. A tool that called the API would be
a tool whose answer depended on quota, and a chat window is the worst place to
discover an account is out of it.

Every tool also returns `Figure`s. That is what the number check matches a
reply against: a figure the model was given is a number it may say, and
anything else is invented. See `ppcway.metric.figures.unmatched`.

**`get_auction_insights` cannot do what its name says, and says so.** Auction
Insights is a report in the Google Ads interface and is not exposed by the
Google Ads API at all -- there is no resource for it, in any version. What the
API does give is impression share: how much of the available auction an account
appeared in, and how much it lost to budget and to rank. That is the useful
part of the same question and it is what this returns. The name is kept because
the brief names it, and the description tells the model what it is actually
getting so it cannot answer a question about named competitors as though it
had the data. This is worth raising with the client rather than leaving in a
docstring.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any, Final
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ppcway.ads.mirror import MICRO, CampaignDay, ExternalChange, MirrorCampaign, SearchTermDay
from ppcway.ads.numbers import account_numbers
from ppcway.chat.untrusted import mark_all
from ppcway.metric.figures import Figure, Period, Scope, Unit
from ppcway.metric.pacing import project
from ppcway.metric.verdicts import for_counts
from ppcway.opt.models import OptimizationAction

log = logging.getLogger(__name__)

#: The longest window any tool will look back over. A question about two years
#: ago is a question the mirror cannot answer honestly, and a tool that
#: silently returned ninety days for a request for seven hundred would make
#: the model confident about a period it never saw.
MOST_DAYS: Final = 365

#: How many rows a list-shaped tool returns at most. A chat answer is read, not
#: scrolled, and two hundred search terms in a context window is mostly cost.
MOST_ROWS: Final = 25


@dataclass(frozen=True, slots=True)
class Asked:
    """One tool call: the scope it may read, and the arguments it was given.

    The scope is not in the arguments and cannot be. That is the whole of the
    scope enforcement: a model that has been talked into asking about somebody
    else's account has no field in which to say so.
    """

    session: Session
    organization_id: UUID
    customer_id: str
    currency: str
    args: dict[str, Any]
    today: date
    #: What this turn's read tools have offered as proposable, by opaque
    #: handle. None for a turn with no write tool, which is every turn before
    #: phase 3.3 and every turn where the write path is shut.
    handles: Any = None
    #: The business's Google Ads connection, needed only by the write tool,
    #: which judges a proposal against the account's standing before writing
    #: it. Read tools neither need nor get it.
    connection: Any = None
    organization_id_for_write: Any = None

    def days(self, *, default: int = 30) -> int:
        """The window asked for, clamped to something the mirror can answer."""
        want = self.args.get("days", default)
        try:
            days = int(want)
        except (TypeError, ValueError):
            return default
        return max(1, min(MOST_DAYS, days))

    def window(self, *, default: int = 30) -> Period:
        return Period.last(self.days(default=default), until=self.today)


@dataclass(frozen=True, slots=True)
class Answer:
    """What a tool found: the data for the model, and the figures to check it."""

    data: dict[str, Any]
    figures: tuple[Figure, ...] = ()
    #: One line for the streamed status, in the words a person would use.
    doing: str = ""


@dataclass(frozen=True, slots=True)
class Tool:
    """One typed, read-only lookup."""

    name: str
    about: str
    takes: dict[str, Any]
    #: Result fields written by somebody outside PPCWay. Declared per tool
    #: rather than guessed at, and a test asserts every field a tool can
    #: return is either listed here or deliberately recorded as ours.
    theirs: frozenset[str] = frozenset()
    run: Callable[[Asked], Answer] = field(default=lambda _: Answer(data={}))

    def __call__(self, asked: Asked) -> Answer:
        found = self.run(asked)
        return Answer(
            data=mark_all(found.data, fields=self.theirs),
            figures=found.figures,
            doing=found.doing,
        )

    def as_schema(self) -> dict[str, Any]:
        """The definition the model is given."""
        return {"name": self.name, "description": self.about, "input_schema": self.takes}


_DAYS = {
    "type": "object",
    "properties": {
        "days": {
            "type": "integer",
            "minimum": 1,
            "maximum": MOST_DAYS,
            "description": "How many days back to look. Defaults to 30.",
        }
    },
    "additionalProperties": False,
}

_NOTHING: Final[dict[str, Any]] = {
    "type": "object",
    "properties": {},
    "additionalProperties": False,
}


def _money(value: float, asked: Asked, name: str, scope: Scope, window: Period) -> Figure:
    return Figure(
        name=name,
        value=round(value, 2),
        unit=Unit.MONEY,
        currency=asked.currency or "",
        period=window,
        scope=scope,
        as_of=datetime.now(UTC),
    )


def _count(value: float, name: str, scope: Scope, window: Period) -> Figure:
    return Figure(
        name=name,
        value=float(value),
        unit=Unit.COUNT,
        period=window,
        scope=scope,
        as_of=datetime.now(UTC),
    )


# --- 1. what the account did -------------------------------------------------


def _metrics(asked: Asked) -> Answer:
    window = asked.window()
    held = account_numbers(
        asked.session,
        asked.customer_id,
        days=window.days,
        currency=asked.currency,
        today=asked.today,
    )
    if not held.read:
        return Answer(
            data={"read": False, "why": held.trouble or "This account has not been read yet."},
            doing="looking at what the account did",
        )
    whole = Scope(kind="account")
    verdict, words, test = for_counts(held.leads, held.leads_before, what="leads")
    figures = (
        _money(held.cost, asked, "spend", whole, window),
        _count(held.leads, "leads", whole, window),
        _count(held.clicks, "clicks", whole, window),
        _count(held.impressions, "impressions", whole, window),
        _money(held.cost_per_lead, asked, "cost_per_lead", whole, window),
    )
    return Answer(
        data={
            "read": True,
            "days": window.days,
            "from": window.start.isoformat(),
            "to": window.end.isoformat(),
            "currency": asked.currency,
            "spend": held.cost,
            "leads": held.leads,
            "calls": held.calls,
            "forms": held.forms,
            "clicks": held.clicks,
            "impressions": held.impressions,
            "cost_per_lead": held.cost_per_lead,
            "leads_before": held.leads_before,
            "spend_before": held.cost_before,
            "leads_verdict": verdict,
            "leads_verdict_words": words,
            "leads_test": test,
        },
        figures=figures,
        doing="looking at what the account did",
    )


# --- 2. what people actually typed -------------------------------------------


def _search_terms(asked: Asked) -> Answer:
    window = asked.window()
    rows = asked.session.execute(
        select(
            func.max(SearchTermDay.term).label("term"),
            func.sum(SearchTermDay.clicks).label("clicks"),
            func.sum(SearchTermDay.cost_micros).label("cost_micros"),
            func.sum(SearchTermDay.conversions).label("conversions"),
            func.max(SearchTermDay.status).label("status"),
            SearchTermDay.term_hash.label("term_hash"),
            func.max(SearchTermDay.ad_group_id).label("ad_group_id"),
        )
        .where(
            SearchTermDay.customer_id == asked.customer_id,
            SearchTermDay.day >= window.start,
            SearchTermDay.day <= window.end,
        )
        .group_by(SearchTermDay.term_hash)
        .order_by(func.sum(SearchTermDay.cost_micros).desc())
        .limit(MOST_ROWS)
    ).all()
    # `term_hash` and `ad_group_id` are selected so a handle can point at the
    # row without the model ever seeing either.

    terms: list[dict[str, Any]] = []
    for row in rows:
        one: dict[str, Any] = {
            "term": row.term,
            "clicks": int(row.clicks or 0),
            "spend": round((row.cost_micros or 0) / MICRO, 2),
            "leads": float(row.conversions or 0),
            "already_handled": row.status in {"ADDED", "EXCLUDED", "ADDED_EXCLUDED"},
        }
        # A handle, so the model can propose on this without naming it. Only
        # for a term there is something to propose about: one already added or
        # excluded has nothing to do, and offering a handle would invite a
        # proposal the rule would then refuse.
        if asked.handles is not None and not one["already_handled"]:
            one["handle"] = asked.handles.offer(
                "search_term",
                label=str(row.term),
                term_hash=row.term_hash,
                ad_group_id=row.ad_group_id,
            )
        terms.append(one)
    figures = tuple(
        _money(
            float(str(term["spend"])),
            asked,
            "search_term_spend",
            Scope(kind="search_term", id=str(n)),
            window,
        )
        for n, term in enumerate(terms)
    )
    return Answer(
        data={"days": window.days, "currency": asked.currency, "terms": terms},
        figures=figures,
        doing="reading what people searched for",
    )


# --- 3. how much of the auction we were in -----------------------------------


def _auction_insights(asked: Asked) -> Answer:
    """Impression share, which is not Auction Insights. See the module note."""
    window = asked.window()
    rows = asked.session.execute(
        select(
            CampaignDay.campaign_id,
            func.avg(CampaignDay.search_share).label("share"),
            func.avg(CampaignDay.lost_to_budget).label("budget"),
            func.avg(CampaignDay.lost_to_rank).label("rank"),
        )
        .where(
            CampaignDay.customer_id == asked.customer_id,
            CampaignDay.day >= window.start,
            CampaignDay.day <= window.end,
        )
        .group_by(CampaignDay.campaign_id)
    ).all()
    names = {
        c.campaign_id: c.name
        for c in asked.session.scalars(
            select(MirrorCampaign).where(MirrorCampaign.customer_id == asked.customer_id)
        )
    }
    campaigns = [
        {
            "campaign": names.get(row.campaign_id, row.campaign_id),
            "share_of_auction": None if row.share is None else round(float(row.share), 4),
            "lost_to_budget": None if row.budget is None else round(float(row.budget), 4),
            "lost_to_rank": None if row.rank is None else round(float(row.rank), 4),
            # Google caps anything above 90% and will not say what it really
            # was, so a figure at the cap means "90% or better".
            "capped": row.share is not None and float(row.share) >= 0.9,
        }
        for row in rows
    ]
    return Answer(
        data={
            "days": window.days,
            "campaigns": campaigns,
            "what_this_is_not": (
                "This is impression share, not Auction Insights. The Google Ads API"
                " does not expose Auction Insights, so PPCWay cannot see which named"
                " competitors appeared beside these ads. Do not answer as though it"
                " could."
            ),
        },
        figures=(),
        doing="checking how much of the auction the ads appeared in",
    )


# --- 4. what changed, and who changed it -------------------------------------


def _change_history(asked: Asked) -> Answer:
    window = asked.window()
    since = datetime.combine(window.start, datetime.min.time(), tzinfo=UTC)
    theirs = asked.session.scalars(
        select(ExternalChange)
        .where(
            ExternalChange.customer_id == asked.customer_id,
            ExternalChange.noticed_at >= since,
        )
        .order_by(ExternalChange.noticed_at.desc())
        .limit(MOST_ROWS)
    ).all()
    ours = asked.session.scalars(
        select(OptimizationAction)
        .where(
            OptimizationAction.customer_id == asked.customer_id,
            OptimizationAction.created_at >= since,
        )
        .order_by(OptimizationAction.created_at.desc())
        .limit(MOST_ROWS)
    ).all()
    return Answer(
        data={
            "days": window.days,
            "changed_in_google_ads": [
                {
                    "what": change.label,
                    "summary": change.summary,
                    "when": change.noticed_at.isoformat() if change.noticed_at else "",
                }
                for change in theirs
            ],
            "changed_by_ppcway": [
                {
                    "what": action.target_label,
                    "kind": action.kind,
                    "status": action.status,
                    "when": action.created_at.isoformat() if action.created_at else "",
                    "reason": action.reason,
                }
                for action in ours
            ],
        },
        doing="looking at what has changed lately",
    )


# --- 5. where the month is heading -------------------------------------------


def _pacing(asked: Asked) -> Answer:
    month_start = asked.today.replace(day=1)
    spent = (
        asked.session.scalar(
            select(func.sum(CampaignDay.cost_micros)).where(
                CampaignDay.customer_id == asked.customer_id,
                CampaignDay.day >= month_start,
                CampaignDay.day <= asked.today,
            )
        )
        or 0
    ) / MICRO
    budget = (
        asked.session.scalar(
            select(func.sum(MirrorCampaign.budget_micros)).where(
                MirrorCampaign.customer_id == asked.customer_id,
                MirrorCampaign.gone_at.is_(None),
                MirrorCampaign.status == "ENABLED",
            )
        )
        or 0
    ) / MICRO
    said = project(
        spent=round(spent, 2),
        daily_budget=round(budget, 2),
        today=asked.today,
        currency=asked.currency,
    )
    window = Period(start=month_start, end=asked.today)
    whole = Scope(kind="account")
    return Answer(
        data={
            "spent_so_far": said.spent,
            "daily_budget": said.daily_budget,
            "a_day_so_far": said.a_day_so_far,
            "heading_for": said.projected,
            "most_google_will_charge": said.most_google_will_charge,
            "days_gone": said.days_gone,
            "days_left": said.days_left,
            "pace": said.pace.value,
            "words": said.words,
            "runs_out_on": said.runs_out_on.isoformat() if said.runs_out_on else None,
            "currency": asked.currency,
        },
        figures=(
            _money(said.spent, asked, "spend_month_to_date", whole, window),
            _money(said.projected, asked, "spend_projected", whole, window),
            _money(said.daily_budget, asked, "daily_budget", whole, window),
        ),
        doing="working out where this month's spend is heading",
    )


# --- 6. why a number moved ---------------------------------------------------


def _explain_change(asked: Asked) -> Answer:
    """Why one figure moved, from the decomposition rather than from a guess."""
    from ppcway.metric.because import RECIPES, because

    what = str(asked.args.get("figure", "")).strip()
    if what not in RECIPES:
        return Answer(
            data={
                "explained": False,
                "why": (
                    f"{what or 'that'} is not a figure PPCWay works out from other"
                    f" figures, so there is nothing to split it into. The ones that"
                    f" can be explained are: {', '.join(sorted(RECIPES))}."
                ),
            },
            doing="checking whether that number can be explained",
        )

    window = asked.window()
    before = window.before()
    now = account_numbers(
        asked.session,
        asked.customer_id,
        days=window.days,
        currency=asked.currency,
        today=asked.today,
    )
    whole = Scope(kind="account")
    parts = _parts_for(now, asked, whole, window)
    target = parts.get(what)
    if target is None:
        return Answer(
            data={"explained": False, "why": "We do not hold both periods for that."},
            doing="checking whether that number can be explained",
        )

    said = because(target, parts)
    return Answer(
        data={
            "figure": what,
            "explained": said.explained,
            "change": said.change,
            "words": said.words,
            "parts": [
                {
                    "what": part.label,
                    "moved": part.moved,
                    "share_of_change": part.share,
                    "amount": part.amount,
                }
                for part in said.factors
            ],
            "from": before.slug,
            "to": window.slug,
        },
        figures=(target, *parts.values()),
        doing=f"working out why {what.replace('_', ' ')} moved",
    )


def _parts_for(held: Any, asked: Asked, whole: Scope, window: Period) -> dict[str, Figure]:
    """Every figure a decomposition might need, with its earlier value."""
    at = datetime.now(UTC)

    def one(name: str, value: float, was: float, unit: Unit) -> Figure:
        return Figure(
            name=name,
            value=value,
            before=was,
            unit=unit,
            currency=asked.currency if unit is Unit.MONEY else "",
            period=window,
            scope=whole,
            as_of=at,
        )

    clicks, clicks_before = float(held.clicks), float(held.clicks_before or 0)
    rate = held.leads / clicks if clicks else 0.0
    rate_before = (held.leads_before / clicks_before) if clicks_before else 0.0
    cpc = held.cost / clicks if clicks else 0.0
    cpc_before = (held.cost_before / clicks_before) if clicks_before else 0.0
    return {
        "leads": one("leads", held.leads, held.leads_before, Unit.COUNT),
        "spend": one("spend", held.cost, held.cost_before, Unit.MONEY),
        "clicks": one("clicks", clicks, clicks_before, Unit.COUNT),
        "conversion_rate": one("conversion_rate", rate, rate_before, Unit.RATIO),
        "cost_per_click": one("cost_per_click", cpc, cpc_before, Unit.MONEY),
        "cost_per_lead": one(
            "cost_per_lead",
            held.cost_per_lead,
            held.cost_per_lead_before,
            Unit.MONEY,
        ),
    }


# --- 7. the report, as a person would read it --------------------------------


def _report(asked: Asked) -> Answer:
    from ppcway.ads.reports import report_for

    window = asked.window()
    said = report_for(
        asked.session,
        asked.customer_id,
        days=window.days,
        currency=asked.currency,
        today=asked.today,
    )
    body = said.as_dict()
    return Answer(
        data={"report": body},
        figures=(),
        doing="pulling together the report",
    )


# --- 8. how PPCWay itself works ----------------------------------------------

#: What Otto may say about PPCWay. Written here rather than left to the model,
#: because a model answering "how do I turn off auto-apply" from memory will
#: eventually describe a button that does not exist.
HELP: Final[dict[str, str]] = {
    "what otto does": (
        "Otto reads your Google Ads account every night, finds things worth "
        "changing, and puts them in your inbox with the figures behind them. "
        "Nothing is changed without your yes unless you have turned that on."
    ),
    "auto apply": (
        "Only the owner can let Otto make changes without asking, and only two "
        "kinds: excluding searches that cost money and never led to anybody "
        "getting in touch, and pausing ads Google has refused. You can turn it "
        "off at any moment from your settings, and it stops straight away."
    ),
    "undo": (
        "Any change PPCWay made can be put back for thirty days from your "
        "activity feed. Money already spent and Google's own learning about "
        "your ads do not come back."
    ),
    "limits": (
        "PPCWay will not move a budget by more than 20% in one change without a "
        "PPCWay expert signing it off, never by more than 50% in one change, and "
        "never more than ten changes a week on one account."
    ),
    "who can see my data": (
        "You and anyone you invite. PPCWay support can look only if you ask, and "
        "every look is written down."
    ),
}


def _help(asked: Asked) -> Answer:
    about = str(asked.args.get("about", "")).strip().lower()
    words = [text for topic, text in HELP.items() if not about or about in topic]
    if not words:
        words = list(HELP.values())
    return Answer(
        data={"topics": sorted(HELP), "help": words},
        doing="checking how PPCWay handles that",
    )


TOOLS: Final[dict[str, Tool]] = {
    "get_metrics": Tool(
        name="get_metrics",
        about=(
            "What this account did over a window: spend, leads, clicks, impressions"
            " and cost per lead, with the same figures for the window before and a"
            " verdict on whether any change in leads is real or ordinary noise."
        ),
        takes=_DAYS,
        run=_metrics,
    ),
    "get_search_terms": Tool(
        name="get_search_terms",
        about=(
            "What people actually typed to reach these ads, costliest first, with"
            " whether each is already added as a keyword or already excluded."
        ),
        takes=_DAYS,
        theirs=frozenset({"term"}),
        run=_search_terms,
    ),
    "get_auction_insights": Tool(
        name="get_auction_insights",
        about=(
            "How much of the available auction each campaign appeared in, and how"
            " much it lost to its budget and to its ad rank. This is impression"
            " share: the Google Ads API does not expose Auction Insights, so"
            " PPCWay cannot see which named competitors appeared beside these ads."
            " Do not answer questions about named competitors from this."
        ),
        takes=_DAYS,
        theirs=frozenset({"campaign"}),
        run=_auction_insights,
    ),
    "get_change_history": Tool(
        name="get_change_history",
        about=(
            "What has changed lately, in two lists: changes somebody made in"
            " Google Ads itself, and changes PPCWay proposed or made."
        ),
        takes=_DAYS,
        theirs=frozenset({"what", "summary"}),
        run=_change_history,
    ),
    "get_pacing_forecast": Tool(
        name="get_pacing_forecast",
        about=(
            "Where this month's spend is heading, against the budget, with the most"
            " Google will charge in a month and the day the allowance runs out if"
            " it does."
        ),
        takes=_NOTHING,
        run=_pacing,
    ),
    "explain_change": Tool(
        name="explain_change",
        about=(
            "Why one figure moved, split exactly between the things that moved it."
            " Answers nothing unless the change was larger than ordinary noise,"
            " because a confident story about noise is worse than silence."
        ),
        takes={
            "type": "object",
            "properties": {
                "figure": {
                    "type": "string",
                    "enum": ["leads", "clicks", "spend", "cost_per_lead"],
                    "description": "Which figure to explain.",
                },
                "days": {"type": "integer", "minimum": 1, "maximum": MOST_DAYS},
            },
            "required": ["figure"],
            "additionalProperties": False,
        },
        run=_explain_change,
    ),
    "generate_report": Tool(
        name="generate_report",
        about=(
            "The report PPCWay shows on screen: every figure with a verdict beside"
            " it and the name of the test used, plus what needs a person."
        ),
        takes=_DAYS,
        theirs=frozenset({"label"}),
        run=_report,
    ),
    "search_help": Tool(
        name="search_help",
        about=(
            "How PPCWay itself works: what Otto does, auto-apply, undo, the limits"
            " on changes, and who can see an account's data. Use this rather than"
            " answering from memory about PPCWay's own behaviour."
        ),
        takes={
            "type": "object",
            "properties": {
                "about": {"type": "string", "description": "A topic, or empty for all."}
            },
            "additionalProperties": False,
        },
        run=_help,
    ),
}


def schemas() -> list[dict[str, Any]]:
    """The tool definitions given to the model, in a stable order.

    Stable because the tool list is part of the cached prompt prefix, and a
    set's iteration order changing between processes would quietly cost a cache
    hit on every first turn.
    """
    return [TOOLS[name].as_schema() for name in sorted(TOOLS)]


def run(name: str, asked: Asked) -> Answer:
    """One tool by name, refusing an unknown one rather than guessing."""
    tool = TOOLS.get(name)
    if tool is None:
        return Answer(
            data={"error": f"There is no tool called {name!r}."},
            doing="",
        )
    try:
        return tool(asked)
    except Exception:
        # A tool that raises must not take the conversation down with it: the
        # model is told the lookup failed and can say so or try another.
        log.exception("tool %s failed", name)
        return Answer(
            data={"error": "That lookup did not work. Say so rather than guessing."},
            doing="",
        )
