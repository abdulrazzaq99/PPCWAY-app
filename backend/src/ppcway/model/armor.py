"""Model Armor: screening what a merchant typed before it reaches a model.

The brief requires it on every chat message, and `model.service` already fails
closed without it -- `Job.CHAT` with no screener raises `NotScreened` rather
than chatting unscreened. This is the screener that satisfies that, so chat can
work at all.

**It must fail closed too, and that is the whole design.** A screener that
returns "clean" when it could not reach Model Armor is worse than no screener:
it converts an outage into a silent policy bypass, and the logs would show a
clean verdict on every message. So anything other than a successful screening
with a usable verdict blocks. An outage stops chat, which is the correct
failure for a control the brief calls mandatory.

**The regional host, not the global one.** Google's own two pages disagree: the
API reference shows `modelarmor.googleapis.com`, and the how-to says, in a
note, "To sanitize prompts and responses, you must use regional endpoints."
Every SDK sample uses the regional host. So this uses
`modelarmor.{location}.rep.googleapis.com`, taking the location out of the
template name rather than from a second setting that could drift from it.

**One thing to know about the region.** Google documents that in
`northamerica-northeast2` -- where this service happens to run -- prompt
injection and responsible-AI checks on non-English text come back as skipped
rather than judged. The template therefore wants to live in `us-central1`
alongside Vertex, which is also where the client's residency decision puts
model processing. A template in a region that silently skips checks would
produce clean verdicts that mean nothing, so `location_of` surfaces the region
and `WEAK_FOR_OTHER_LANGUAGES` names the ones to avoid.

**The verdict is the top-level `filterMatchState`, not any one filter's.**
Reading individual filters would mean deciding here which of Google's filters
matter, and that decision belongs in the template, where the client can change
it without a deploy.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Final

import httpx

from ppcway.model.service import Screening

log = logging.getLogger(__name__)

#: What a merchant is told when their message is blocked. Deliberately short
#: and not an accusation: the common case is somebody pasting a customer's
#: details in, not an attack, and either way the words are the same because
#: telling them which filter fired is telling an attacker which filter fired.
BLOCKED_WORDS: Final = (
    "We could not send that message. Please rewrite it without any personal"
    " details -- names, addresses, card numbers -- and ask again."
)

#: What they are told when screening itself failed. Different words, because
#: the honest thing is that this is our problem and not their message.
UNAVAILABLE_WORDS: Final = (
    "We could not check that message just now, so we have not sent it. Please"
    " try again in a moment."
)

#: Regions where Google documents that prompt-injection and responsible-AI
#: checks skip non-English text instead of judging it. A template here returns
#: clean verdicts that do not mean what they say.
WEAK_FOR_OTHER_LANGUAGES: Final = frozenset({"asia-south1", "northamerica-northeast2"})

MATCH_FOUND: Final = "MATCH_FOUND"
NO_MATCH: Final = "NO_MATCH_FOUND"
INVOCATION_OK: Final = "SUCCESS"

#: Model Armor is in the path of every chat message a merchant sends, so it
#: cannot be allowed to hang the request.
TIMEOUT: Final = httpx.Timeout(10.0, connect=5.0)


def location_of(template: str) -> str:
    """The region a template lives in, read out of its own name.

    Taken from the name rather than configured separately: two settings that
    must agree are two settings that can disagree, and the failure would be a
    404 at the moment a merchant typed something.
    """
    parts = template.split("/")
    if len(parts) >= 4 and parts[0] == "projects" and parts[2] == "locations":
        return parts[3]
    raise ValueError(
        f"a Model Armor template is named 'projects/.../locations/.../templates/...'"
        f" and got {template!r}. The region is read out of the name, so a malformed"
        f" name has no region to send to."
    )


@dataclass(frozen=True, slots=True)
class ModelArmor:
    """Screens a merchant's words through one Model Armor template.

    Authentication is Google's, from the environment's application default
    credentials, exactly as in `model.service`. There is no key here to leak.
    """

    #: "projects/{project}/locations/{location}/templates/{template}".
    template: str
    #: Injected so a test drives this without credentials and without network.
    client: httpx.Client | None = None
    #: Injected for the same reason. Returns a bearer token.
    token: Any | None = None

    def __post_init__(self) -> None:
        location_of(self.template)  # Fail at construction, not mid-conversation.

    @property
    def location(self) -> str:
        return location_of(self.template)

    @property
    def checks_other_languages(self) -> bool:
        """False where this region skips the checks instead of running them."""
        return self.location not in WEAK_FOR_OTHER_LANGUAGES

    @property
    def url(self) -> str:
        host = f"modelarmor.{self.location}.rep.googleapis.com"
        return f"https://{host}/v1/{self.template}:sanitizeUserPrompt"

    def _bearer(self) -> str:
        if self.token is not None:
            return str(self.token())
        import google.auth
        import google.auth.transport.requests

        credentials, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        credentials.refresh(google.auth.transport.requests.Request())  # type: ignore[no-untyped-call]
        return str(credentials.token)

    def check(self, text: str) -> Screening:
        """Screen one message. Blocks on anything that is not a clean pass.

        Never raises. A screener that raised would turn an outage into a
        traceback in the chat endpoint; blocking says the same thing in words a
        merchant can act on, and the reason is logged for whoever is on call.
        """
        if not text.strip():
            # Nothing to screen. Not a pass: an empty message should not reach
            # a model either, and saying "clean" about nothing is a lie.
            return Screening(verdict="blocked", because="There was no message to send.")

        own = self.client is None
        client = self.client or httpx.Client(timeout=TIMEOUT)
        try:
            said = client.post(
                self.url,
                json={"userPromptData": {"text": text}},
                headers={
                    "Authorization": f"Bearer {self._bearer()}",
                    "Content-Type": "application/json",
                },
            )
        except (httpx.HTTPError, OSError) as exc:
            log.warning("Model Armor could not be reached: %s", exc)
            return Screening(verdict="blocked", because=UNAVAILABLE_WORDS)
        except Exception as exc:  # noqa: BLE001 -- credentials can fail in many ways
            # google.auth raises several unrelated types, and every one of them
            # has to block rather than escape into the chat endpoint.
            log.warning("Model Armor screening failed before the request: %s", exc)
            return Screening(verdict="blocked", because=UNAVAILABLE_WORDS)
        finally:
            if own:
                client.close()

        if said.status_code != 200:
            # 403 here usually means the service account lacks
            # modelarmor.templates.useToSanitizeUserPrompt on the template.
            log.warning("Model Armor answered %s for %s", said.status_code, self.template)
            return Screening(verdict="blocked", because=UNAVAILABLE_WORDS)

        return self._read(said)

    def _read(self, said: httpx.Response) -> Screening:
        """Turn one response into a verdict, treating anything unclear as blocked."""
        try:
            body = said.json()
        except ValueError:
            log.warning("Model Armor sent a body that is not JSON")
            return Screening(verdict="blocked", because=UNAVAILABLE_WORDS)

        result = body.get("sanitizationResult") or {}
        invocation = result.get("invocationResult", "")
        state = result.get("filterMatchState", "")

        if invocation and invocation != INVOCATION_OK:
            log.warning("Model Armor did not complete: invocationResult=%s", invocation)
            return Screening(verdict="blocked", because=UNAVAILABLE_WORDS)
        if state == MATCH_FOUND:
            log.info("Model Armor blocked a message: %s", _which_fired(result))
            return Screening(verdict="blocked", because=BLOCKED_WORDS)
        if state == NO_MATCH:
            return Screening(verdict="clean")

        # An unrecognised state. Blocking an unknown verdict is the whole point
        # of failing closed: a new enum value must not read as a pass.
        log.warning("Model Armor sent an unrecognised filterMatchState: %r", state)
        return Screening(verdict="blocked", because=UNAVAILABLE_WORDS)


def _which_fired(result: dict[str, Any]) -> str:
    """Which filters matched, for the log only.

    Never shown to a merchant: telling somebody which filter fired tells an
    attacker which filter fired, and the words they see are the same either way.
    """
    fired: list[str] = []
    for name, wrapper in (result.get("filterResults") or {}).items():
        if not isinstance(wrapper, dict):
            continue
        for inner in wrapper.values():
            if not isinstance(inner, dict):
                continue
            found = inner.get("matchState") or (inner.get("inspectResult") or {}).get("matchState")
            if found == MATCH_FOUND:
                fired.append(str(name))
                break
    return ", ".join(sorted(fired)) or "no filter named"
