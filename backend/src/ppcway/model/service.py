"""The one door to Claude. Nothing else in this codebase calls a model.

The shape follows the proof of concept's `llm` package, and the reason it is a
service rather than a helper is the client's brief: *the model service and chat
code have no import path to the Google Ads token vault and cannot fetch URLs*.
A constraint of that kind is only worth stating if something enforces it, so
`tests/model/test_boundaries.py` reads the imports of this package and fails if
one appears. Blueprint §18.2: an architectural rule that is not enforced
mechanically decays.

**Vertex AI, in a named United States region.** `region="us-central1"`, from
settings, and `"global"` is refused outright rather than accepted as a shorter
spelling: the brief says the global endpoint is not used, and the difference
between the two is which countries a prompt may be processed in.

`"us"`, the United States multi-region, is not usable and that was established
by asking rather than by reading: `rawPredict` on an Anthropic model there
answers **501 UNIMPLEMENTED**. The multi-region serves Google's own publisher
models and not this one. `us-central1` lists all thirteen Anthropic models;
`us-east5` lists none. So the default is a named US region, which keeps the
client's residency decision of 30 October -- processing in the United States --
while actually being a place the request can land. There is no Anthropic API
key anywhere in this package -- authentication is Google's, from the
environment's own application default credentials, which is also why nothing
here has a secret to leak.

**Every answer names the model and the prompt version, and neither may be
blank.** Blueprint §7.6. That is not bookkeeping: it is the only way to answer
"which merchants got the bad headline" once the prompt that wrote it has been
fixed, and a provider that forgets to fill it in is the one that ships an
untraceable ad. `Answer.__post_init__` refuses rather than trusting the caller.

**The model is never asked to do arithmetic.** Every figure a merchant reads is
computed in our own code and passed in; the model's job is the sentence around
it. That is a design rule rather than something this file can check, and the
check that enforces it -- every number in a reply matched against the figures
that turn was given -- belongs with the caller, in phases 1.2 and 3.1.

**A refusal is an ordinary outcome.** These models decline some requests with
HTTP 200 and `stop_reason: "refusal"`, so `stop_reason` is read before the
content on every call, and an empty answer is returned rather than an
exception: a refused ad draft is a fallback to the category template, not a
crash.
"""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Final, Protocol, runtime_checkable

import anthropic

from ppcway.model.jobs import Job, Tier, tier_for

log = logging.getLogger(__name__)

#: The endpoint the brief says to use, and the one it says not to.
#: A named US region rather than the `us` multi-region, which answers 501
#: UNIMPLEMENTED for Anthropic models. Still the United States, as the client
#: decided; just a region that serves them.
US_REGION = "us-central1"
REFUSED_REGION = "global"


class ModelUnavailable(RuntimeError):
    """The model could not be reached or is not configured. Says which, never a secret."""


class NotScreened(RuntimeError):
    """Input screening was required for this job and no screener was configured.

    Fail closed. The brief requires Model Armor on every chat message; a
    deployment that cannot screen must refuse to chat rather than chat
    unscreened, in the same way an unconfigured spend ceiling refuses a budget
    change rather than allowing it.
    """


@dataclass(frozen=True, slots=True)
class Screening:
    """What the input screener made of one message."""

    #: "clean", "blocked", or "not_screened" where screening did not apply.
    verdict: str
    #: Why it was blocked, in words a person can be shown.
    because: str = ""

    @property
    def blocked(self) -> bool:
        return self.verdict == "blocked"


@runtime_checkable
class Screener(Protocol):
    """Model Armor, or anything shaped like it.

    Runtime-checkable for the same reason `gateway.port.Door` is: a seam the
    deployment plugs a real implementation into is a seam worth being able to
    assert about.
    """

    def check(self, text: str) -> Screening: ...


@dataclass(frozen=True, slots=True)
class ToolCall:
    """One lookup the model wants done, with the arguments it chose."""

    id: str
    name: str
    args: dict[str, Any]


@dataclass(frozen=True, slots=True)
class Answer:
    """What a model said, and everything needed to trace it back."""

    text: str
    model: str
    prompt_version: str
    stop_reason: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    took_ms: int = 0
    screening: Screening = field(default_factory=lambda: Screening(verdict="not_screened"))
    #: Lookups the model wants done before it can answer. Empty when it is
    #: answering rather than asking.
    tool_calls: tuple[ToolCall, ...] = ()
    #: The reply's content blocks as they came back, to be sent straight back
    #: on the next turn. Passed through rather than rebuilt: a thinking block
    #: the API can still read must go back unchanged, and reconstructing one
    #: from its text is how it stops being readable.
    raw_content: tuple[Any, ...] = ()

    def __post_init__(self) -> None:
        if not self.model or not self.prompt_version:
            raise ValueError(
                f"an answer must name the model and the prompt version that produced it,"
                f" and got model={self.model!r}, prompt_version={self.prompt_version!r}."
                f" Blueprint §7.6: a live ad has to trace back to the exact prompt and"
                f" model, which is how the merchants reached by a bad prompt are found"
                f" after that prompt has been fixed."
            )

    @property
    def refused(self) -> bool:
        """The model declined. An outcome, not a fault."""
        return self.stop_reason == "refusal"


#: Jobs where input screening is not optional. The brief names chat; a card's
#: reason is written from our own computed figures and never from a merchant's
#: words, so there is nothing of theirs to screen.
MUST_SCREEN = frozenset({Job.CHAT})


@dataclass(frozen=True, slots=True)
class Models:
    """How this deployment reaches Claude. Built once, passed where needed."""

    project: str
    region: str = US_REGION
    prompt_version: str = ""
    #: Injected, so a test drives this without credentials and without network.
    client: Any | None = None
    screener: Screener | None = None

    def __post_init__(self) -> None:
        if self.region == REFUSED_REGION:
            raise ValueError(
                "the global endpoint is not used: the client's brief pins model"
                " processing to the United States multi-region, and 'global'"
                " would let a prompt be served from anywhere. Set"
                f" VERTEX_REGION to {US_REGION!r} or another named US region."
            )

    @property
    def ready(self) -> bool:
        return bool(self.project and self.region and self.prompt_version)

    def _client(self) -> Any:
        if self.client is not None:
            return self.client
        if not self.ready:
            raise ModelUnavailable(
                "the model service is not set up: VERTEX_PROJECT, VERTEX_REGION and"
                " MODEL_PROMPT_VERSION must all be set. Nothing was sent."
            )
        # Google's credentials, from the environment. No API key is passed,
        # because there is none in this deployment to pass.
        return anthropic.AnthropicVertex(project_id=self.project, region=self.region)

    def ask(
        self,
        job: Job,
        *,
        system: str,
        said: Sequence[dict[str, Any]] | str,
        organization_id: uuid.UUID | None = None,
        customer_id: str = "",
        tools: Sequence[dict[str, Any]] | None = None,
    ) -> Answer:
        """Put one question to the model for one job, and answer with provenance.

        `system` is sent as a cached block: it is the part that does not change
        between requests, and the cache is a prefix match, so anything volatile
        belongs in `said` and not here. A per-request timestamp in the system
        prompt is the usual way a cache hit rate quietly becomes zero.

        No `temperature`, `top_p` or `top_k`: every current model rejects them.
        No assistant prefill, which these models also reject.

        `tools` carries PPCWay's own typed, read-only lookups and nothing else.
        `_only_ours` refuses anything that is not one of those -- in
        particular Anthropic's own server tools, because `web_fetch` is
        precisely the capability the client's brief forbids this service. The
        refusal is a check rather than a convention: Vertex does not offer
        those tools to Claude anyway, so without it the property would hold by
        accident of the platform rather than by design.
        """
        tier = tier_for(job)
        messages = [{"role": "user", "content": said}] if isinstance(said, str) else list(said)
        screening = self._screen(job, messages)
        if screening.blocked:
            return Answer(
                text="",
                model=tier.model,
                prompt_version=self.prompt_version or "unscreened",
                stop_reason="blocked",
                screening=screening,
            )

        ours = _only_ours(tools)
        started = time.monotonic()
        try:
            said_back = self._client().messages.create(
                model=tier.model,
                max_tokens=tier.max_tokens,
                **({"tools": ours} if ours else {}),
                system=[
                    {
                        "type": "text",
                        "text": system,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=messages,
                output_config={"effort": tier.effort},
                thinking={"type": "adaptive"},
            )
        except (anthropic.AnthropicError, OSError) as exc:
            # One type out, by design: the SDK has twenty-odd error classes and
            # every caller here does the same one thing about all of them,
            # which is fall back to words written in code. Narrowed to the
            # SDK's own base class and to socket failures rather than catching
            # everything -- a TypeError from our own request-building is a bug
            # in this file and should not be reported as Google being down.
            raise ModelUnavailable(f"the model could not be reached: {exc}") from None
        took = int((time.monotonic() - started) * 1000)
        return self._answer(said_back, tier, took, screening)

    def _screen(self, job: Job, messages: list[dict[str, Any]]) -> Screening:
        """Screen the merchant's own words, where the job requires it."""
        if job not in MUST_SCREEN:
            return Screening(verdict="not_screened")
        if self.screener is None:
            raise NotScreened(
                f"{job.value} requires input screening and no screener is configured."
                " Model Armor is not optional for a message a merchant typed, so"
                " nothing was sent."
            )
        return self.screener.check(_words_of(messages))

    def _answer(self, said: Any, tier: Tier, took_ms: int, screening: Screening) -> Answer:
        """Read the reply, stop reason first."""
        stop = getattr(said, "stop_reason", "") or ""
        usage = getattr(said, "usage", None)
        answer = Answer(
            tool_calls=() if stop == "refusal" else _calls_in(said),
            raw_content=tuple(getattr(said, "content", None) or ()),
            text="" if stop == "refusal" else _text_of(said),
            model=getattr(said, "model", "") or tier.model,
            prompt_version=self.prompt_version,
            stop_reason=stop,
            input_tokens=getattr(usage, "input_tokens", 0) or 0,
            output_tokens=getattr(usage, "output_tokens", 0) or 0,
            cached_tokens=getattr(usage, "cache_read_input_tokens", 0) or 0,
            took_ms=took_ms,
            screening=screening,
        )
        if answer.refused:
            log.info("the model declined a %s request", tier.model)
        return answer


#: Tool types this service will not send, whatever a caller passes. These are
#: Anthropic's own server-side tools: `web_fetch` is the capability the client's
#: brief forbids the model service outright, and the other two are the same
#: argument. Checked rather than assumed, because Vertex does not offer them to
#: Claude today and a property that holds by accident of the platform is a
#: property that changes when the platform does.
NEVER: Final = ("web_search", "web_fetch", "code_execution", "computer", "bash")


def _only_ours(tools: Sequence[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """PPCWay's own typed lookups, and a refusal for anything else."""
    if not tools:
        return []
    out: list[dict[str, Any]] = []
    for tool in tools:
        name = str(tool.get("name", ""))
        kind = str(tool.get("type", ""))
        if any(banned in kind or banned == name for banned in NEVER):
            raise ValueError(
                f"the model service will not send the tool {name or kind!r}. It holds"
                f" PPCWay's own read-only lookups and nothing that fetches a URL or"
                f" runs code, which is the client's brief for this service."
            )
        if "input_schema" not in tool:
            raise ValueError(
                f"the tool {name!r} has no input schema, so it is not one of ours."
                f" Every PPCWay tool declares what it takes."
            )
        out.append(dict(tool))
    return out


def _calls_in(said: Any) -> tuple[ToolCall, ...]:
    """The lookups the model asked for, in the order it asked."""
    out: list[ToolCall] = []
    for block in getattr(said, "content", None) or []:
        if getattr(block, "type", "") != "tool_use":
            continue
        args = getattr(block, "input", None)
        out.append(
            ToolCall(
                id=str(getattr(block, "id", "")),
                name=str(getattr(block, "name", "")),
                args=dict(args) if isinstance(args, dict) else {},
            )
        )
    return tuple(out)


def _text_of(said: Any) -> str:
    """The words, skipping thinking blocks.

    Not `content[0].text`: with adaptive thinking on, the first block is often a
    thinking block, and reading it as the answer gives an empty string on a good
    reply and nobody notices until a merchant sees a blank card.
    """
    parts = []
    for block in getattr(said, "content", None) or []:
        if getattr(block, "type", "") == "text":
            parts.append(getattr(block, "text", "") or "")
    return "\n".join(p for p in parts if p).strip()


def _words_of(messages: list[dict[str, Any]]) -> str:
    """Everything the person actually typed, for the screener to look at."""
    out = []
    for message in messages:
        if message.get("role") != "user":
            continue
        content = message.get("content", "")
        if isinstance(content, str):
            out.append(content)
            continue
        for block in content or []:
            if isinstance(block, dict) and block.get("type") == "text":
                out.append(str(block.get("text", "")))
    return "\n".join(out)
