"""One question to Otto, and the loop that answers it.

Read-only. The brief puts `create_proposal` in phase 3.3 and only after the
write path is live, so there is no write tool here at all -- not a disabled
one, not one behind a flag. A tool that does not exist cannot be called by a
model that has been talked into wanting to call it.

**The four things that make this safe, in the order they matter:**

1. **No tool can change anything.** Every one of the eight reads the mirror.
   This is the only defence that does not depend on getting something right.
2. **No tool learns which account it is reading.** The scope comes from the
   session; no schema has a field for an account, a target or a figure. An
   injected instruction has nothing to redirect.
3. **Every number in the answer is matched** against the figures the tools
   returned this turn. One rewrite, then a fixed line. Same rule as the inbox
   cards, same reason: a model that has invented a figure twice will not be
   talked out of it.
4. **Text written by somebody else is marked** as data, and the system prompt
   says instructions found there are to be reported rather than followed.
   Weakest of the four, and worth having because an injection attempt that
   gets reported gives us a real example from a real account.

**The disclosure is not optional and not the model's to make.** The brief
requires the panel header and the first message of each session to say Otto is
an AI. The first message is prepended here, in code, rather than asked of the
model -- a disclosure the model could forget to make is not a disclosure.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any, Final
from uuid import UUID

from sqlalchemy.orm import Session

from ppcway.chat import tools as toolbox
from ppcway.chat.untrusted import THE_RULE
from ppcway.metric.figures import Figure, unmatched
from ppcway.model.jobs import Job
from ppcway.model.service import Models, ModelUnavailable
from ppcway.org.models import CAN, Role

log = logging.getLogger(__name__)

#: The brief: "Panel header and first message of each session state that Otto
#: is an AI." This is that first message, in code.
DISCLOSURE: Final = (
    "I am Otto, an AI assistant. I can read your Google Ads account and explain "
    "what is happening in it. I cannot change anything here -- changes are "
    "proposed in your inbox, where you decide."
)

#: How many times the model may call tools before the turn is cut off. A loop
#: that could run forever is a loop that will, on the one question that
#: confuses it, while a merchant watches a spinner.
MOST_ROUNDS: Final = 5

#: What to say when the model cannot be trusted with the numbers. Fixed, which
#: is the point: the brief says one rewrite, then a fixed template, and a
#: second generated attempt at a sentence about figures is a second chance to
#: invent one.
FALLBACK: Final = (
    "I have the figures for that but I could not write them up reliably, so I "
    "would rather not guess. The numbers are on your dashboard, and I can try a "
    "narrower question if that helps."
)

HOW_TO_ANSWER: Final = f"""You are Otto, PPCWay's assistant. You help somebody who runs a small \
business and buys Google Ads. They have about thirty seconds and they are not \
a marketer.

How to answer:
- Look things up before answering. You have tools for every figure about this \
account; use them rather than answering from memory, and never estimate a \
number you did not look up.
- Use only numbers your tools returned this turn. Do not work out new ones, \
round differently, add them up, or carry a figure over from earlier in the \
conversation.
- A sentence before a number, a number before a judgement. British English. \
Plain words: "people who clicked", not "click-through rate", unless they used \
the term first.
- Short. Two or three sentences for most questions.
- If a tool says a figure is within the normal range or that there is too \
little data, say that rather than reading a trend into it.
- You cannot change anything. If they ask you to, say that changes are \
proposed in their inbox where they decide, and offer to explain what is there.
- If you do not know, or no tool covers it, say so.

{THE_RULE}"""


@dataclass(frozen=True, slots=True)
class Said:
    """One thing that happened while answering, for the streamed status line."""

    #: "looking", "thinking", "answer", "trouble".
    kind: str
    words: str


@dataclass(slots=True)
class Turn:
    """What came of one question."""

    text: str = ""
    #: Where the words came from: "model", "rewrite", "template" or "refused".
    source: str = ""
    #: Every tool called, in order, with what it was doing.
    looked_up: list[str] = field(default_factory=list)
    #: The figures the tools returned, which is what the answer was checked
    #: against. Kept so a screen can show them beside the words.
    figures: list[Figure] = field(default_factory=list)
    #: Numbers the model used that no figure accounted for, where that
    #: happened. Kept for the prompt log rather than shown to anybody.
    invented: list[float] = field(default_factory=list)
    rounds: int = 0


class NotAllowed(PermissionError):
    """This person may not use the chat."""


def may_chat(role: Role | None) -> None:
    """Who may ask. The role table's own answer, not a second copy of it."""
    if role is None or "view" not in CAN.get(role, frozenset()):
        raise NotAllowed("Your role does not allow you to use Otto.")


def answer(
    models: Models,
    session: Session,
    question: str,
    *,
    organization_id: UUID,
    customer_id: str,
    currency: str,
    role: Role | None,
    history: Sequence[dict[str, Any]] = (),
    today: date | None = None,
) -> Iterator[Said]:
    """Answer one question, yielding status lines and then the answer.

    A generator because the brief asks for streamed status lines: "reading what
    people searched for" while a lookup runs is the difference between a
    four-second wait and a four-second wait that looks broken.
    """
    may_chat(role)
    at = today or datetime.now(UTC).date()
    turn = Turn()

    messages: list[dict[str, Any]] = [*history, {"role": "user", "content": question}]
    figures: list[Figure] = []

    for round_number in range(MOST_ROUNDS):
        turn.rounds = round_number + 1
        try:
            said = models.ask(
                Job.CHAT,
                system=HOW_TO_ANSWER,
                said=messages,
                organization_id=organization_id,
                customer_id=customer_id,
                tools=toolbox.schemas(),
            )
        except ModelUnavailable as exc:
            log.info("chat could not reach the model: %s", exc)
            yield Said(kind="trouble", words="I cannot reach my own brain just now.")
            turn.source = "refused"
            return

        if said.screening.blocked:
            yield Said(
                kind="trouble",
                words=said.screening.because or "I cannot answer that one.",
            )
            turn.source = "refused"
            return

        wanted = said.tool_calls
        if not wanted:
            text, source = _checked(models, said.text, figures, messages)
            turn.text, turn.source = text, source
            turn.figures = figures
            yield Said(kind="answer", words=text)
            return

        # Tool calls. Run them, say what is being done, and go round again.
        results: list[dict[str, Any]] = []
        for call in wanted:
            asked = toolbox.Asked(
                session=session,
                organization_id=organization_id,
                customer_id=customer_id,
                currency=currency,
                args=call.args,
                today=at,
            )
            found = toolbox.run(call.name, asked)
            turn.looked_up.append(call.name)
            if found.doing:
                yield Said(kind="looking", words=found.doing)
            figures.extend(found.figures)
            results.append({"id": call.id, "name": call.name, "result": found.data})
        messages = [
            *messages,
            {"role": "assistant", "content": said.raw_content},
            {"role": "user", "content": _tool_results(results)},
        ]

    # Out of rounds. Honest rather than a sixth attempt.
    yield Said(
        kind="trouble",
        words="That took more looking up than I can do in one go. Try a narrower question.",
    )
    turn.source = "refused"


def _tool_results(results: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Tool results in the shape the model expects them back."""
    return [
        {
            "type": "tool_result",
            "tool_use_id": one["id"],
            "content": _as_text(one["result"]),
        }
        for one in results
    ]


def _as_text(data: Any) -> str:
    import json

    return json.dumps(data, default=str, sort_keys=True)


def _checked(
    models: Models,
    text: str,
    figures: Sequence[Figure],
    messages: Sequence[dict[str, Any]],
) -> tuple[str, str]:
    """Every number in the answer, matched against what the tools returned.

    One rewrite naming the offending figures, then a fixed line. Same as the
    inbox cards, and for the same reason.
    """
    said = (text or "").strip()
    if not said:
        return FALLBACK, "template"

    wrong = unmatched(said, list(figures))
    if not wrong:
        return said, "model"

    log.info("chat answer used %d numbers no tool returned", len(wrong))
    try:
        again = models.ask(
            Job.CHAT,
            system=HOW_TO_ANSWER,
            said=[
                *messages,
                {"role": "assistant", "content": said},
                {
                    "role": "user",
                    "content": (
                        "That answer used "
                        + ", ".join(f"{n:,.10g}" for n in wrong)
                        + ", which no tool returned this turn. Write it again using"
                        " only the numbers your tools gave you, or say you do not"
                        " have that figure."
                    ),
                },
            ],
        )
    except ModelUnavailable:
        return FALLBACK, "template"

    second = (again.text or "").strip()
    if second and not unmatched(second, list(figures)):
        return second, "rewrite"
    return FALLBACK, "template"
