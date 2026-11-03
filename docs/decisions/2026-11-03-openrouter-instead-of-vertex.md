# OpenRouter instead of Vertex AI

**Date:** 3 November 2026
**Status:** code live, not yet switched on (no key issued)
**Decided by:** the owner
**Supersedes, in part:** `2026-10-30-the-client-settled-residency-models-and-auto-apply.md`

## What changed

Claude is reached through OpenRouter rather than Google Vertex AI.
`MODEL_PROVIDER` defaults to `openrouter`. Vertex still works and is one
setting away.

## What this reverses, and what it does not

On 30 October the client wrote: *"Claude on Google Cloud: approved. Go ahead and
enable Claude (Sonnet, Haiku and Opus 5.5) on Vertex AI."* They also set two
conditions that were not about Vertex but were being satisfied **by** Vertex:

1. **No training on customer data.**
2. **Processing in the United States.**

On Vertex both came free, from Google Cloud's own terms and from pinning the
region. Through OpenRouter neither is automatic, so both are now asked for
explicitly in every request:

```
provider: {
  data_collection: "deny",     # refuse any provider that may retain or train
  only: ["anthropic"],         # Anthropic's own first-party serving
  allow_fallbacks: false       # a refused provider stops us, not routes us on
}
```

`allow_fallbacks: false` is what makes the other two mean anything. Without it,
a provider refused for its data policy is a reason to try the next one.

**The client should be told.** This is their condition, re-implemented in a
different place, and the change of vendor is theirs to accept even though the
protection is equivalent. Two things genuinely differ:

- **Residency is now weaker than before.** `only: ["anthropic"]` fixes *who*
  serves the request, not *which country* they serve it from. Vertex let us name
  `us-central1`; OpenRouter has no equivalent guarantee. If the US commitment
  survives in the privacy policy, this needs saying out loud.
- **There is now a credential where there was none.** The Vertex path used the
  runtime service account and held no model key at all. OpenRouter needs one.

## Why it was reasonable anyway

Vertex never came up. The three models sat in the Model Garden catalogue and
every call returned `NOT_FOUND` -- *"your project does not have access to it"* --
because enabling them is a console click-through that only the account holder
can do, and `gcloud ai model-garden models` offers no `accept` or `enable` verb.
Otto's wiring has been finished and proven for days with nothing behind it.
OpenRouter needs an API key and no console ceremony.

## How it is built

**The same SDK and the same request.** OpenRouter serves Anthropic's native
Messages API at `/api/v1/messages`, not only OpenAI's shape -- probing both
paths unauthenticated returns an Anthropic-shaped error from one and an
OpenAI-shaped error from the other. So `anthropic.Anthropic(base_url=...)`
replaces `anthropic.AnthropicVertex(...)` and the body, the cached system
block, the tool schemas and the typed answers are all unchanged.

**A seam, not a replacement.** `Models.provider` picks a branch. Vertex keeps
its tests and still works, because the client approved it and may want it back,
and because a seam with two live sides is a seam that still works.

**Three things that differ on the wire:**

| | Vertex | OpenRouter |
| --- | --- | --- |
| Model name | `claude-sonnet-5-5` | `anthropic/claude-sonnet-5.5` |
| Effort | `output_config.effort`, five rungs | `reasoning.effort`, four rungs |
| Thinking | `thinking: {type: adaptive}` | not sent |

Model names are read off OpenRouter's own model list, not guessed:
`claude-sonnet-5-5` is not a model there, and `for_openrouter` refuses an
unmapped name rather than passing it through to a 404.

`output_config` and `thinking` are first-party parameters. A proxy that does
not recognise one would reject the whole request rather than ignore the field,
so neither is sent.

**Ad drafting loses a rung.** Our ladder is low/medium/high/xhigh/max and
OpenRouter's is low/medium/high, so `xhigh` and `max` both arrive as `high`.
Ad drafting asks for `high` today, so nothing is affected now, and a test
asserts every tier's effort has a mapping so a future `max` cannot silently
become something OpenRouter rejects.

**What did not change, deliberately:** the job decides the model, and nothing
in the application names one; chat is still screened by Model Armor before
anything is sent and still refuses without it; `web_fetch` is still refused
outright rather than filtered; every answer still names the model and prompt
version.

`Answer.model` records what the provider echoed, which on OpenRouter is the
dotted, prefixed spelling. That is the model that actually answered, which
Blueprint §7.6 wants, and it makes the prompt log unambiguous without a
provider column: an `anthropic/` prefix only ever comes from OpenRouter.

## Not verified

**No request has been made.** There is no OpenRouter key yet, so the request
shape, the `provider` block's acceptance on the Anthropic-native endpoint, and
the `reasoning.effort` passthrough are all reasoned from OpenRouter's
documented behaviour and held by tests against a fake client -- not confirmed
against the live API. The first real call may need adjustment. Issue a key and
this gets verified in minutes.

## What is needed

1. An OpenRouter API key, into Secret Manager as `ppcway-openrouter-key`, then
   `OPENROUTER_API_KEY` on the service.
2. The client told that the vendor changed, that their no-training condition is
   now enforced per-request rather than by Google's terms, and that US-only
   processing is no longer guaranteed.
