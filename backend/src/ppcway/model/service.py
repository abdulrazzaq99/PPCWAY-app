"""The one door to Claude. Nothing else in this codebase calls a model.

The shape follows the proof of concept's `llm` package, and the reason it is a
service rather than a helper is the client's brief: *the model service and chat
code have no import path to the Google Ads token vault and cannot fetch URLs*.
A constraint of that kind is only worth stating if something enforces it, so
`tests/model/test_boundaries.py` reads the imports of this package and fails if
one appears. Blueprint §18.2: an architectural rule that is not enforced
mechanically decays.

**Vertex AI, in the United States multi-region.** `region="us"`, from settings,
and `"global"` is refused outright rather than accepted as a shorter spelling:
the brief says the global endpoint is not used, and the difference between the
two is which countries a prompt may be processed in. There is no Anthropic API
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
from typing import Any, Protocol

import anthropic

from ppcway.model.jobs import Job, Tier, tier_for

log = logging.getLogger(__name__)

#: The endpoint the brief says to use, and the one it says not to.
US_MULTI_REGION = "us"
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


class Screener(Protocol):
    """Model Armor, or anything shaped like it."""

    def check(self, text: str) -> Screening: ...


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
    region: str = US_MULTI_REGION
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
                f" VERTEX_REGION to {US_MULTI_REGION!r} or a named US region."
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
    ) -> Answer:
        """Put one question to the model for one job, and answer with provenance.

        `system` is sent as a cached block: it is the part that does not change
        between requests, and the cache is a prefix match, so anything volatile
        belongs in `said` and not here. A per-request timestamp in the system
        prompt is the usual way a cache hit rate quietly becomes zero.

        No `temperature`, `top_p` or `top_k`: every current model rejects them.
        No assistant prefill, which these models also reject. No tools, in this
        phase -- the typed read-only tools arrive with Ask Otto, and a model
        that could fetch a URL is the thing the brief forbids.
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

        started = time.monotonic()
        try:
            said_back = self._client().messages.create(
                model=tier.model,
                max_tokens=tier.max_tokens,
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
