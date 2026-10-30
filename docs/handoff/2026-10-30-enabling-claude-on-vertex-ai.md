# Enabling Claude on Vertex AI: exactly what to accept, and who has to do it

**For:** PPCWay
**Date:** 30 October 2026
**Answers:** "Let me know exactly what needs to be accepted or signed and I'll
take care of it", and the first two open items on your call list.

## The short answer

**There is nothing to sign.** No contract, no order form, no procurement step.
Enabling Claude on Vertex AI is a click-through acceptance inside the Google
Cloud console, and it is done **once per Google Cloud project** by somebody
with the right role on that project. It takes a few minutes.

What that means in practice is five things, in order.

## 1. Two projects, not one

Your brief asks for a separate staging project so evaluation never touches
production data or quota. Everything below has to be done **twice**, once in
each project, because the acceptance and the quota are both per project.

We need you to tell us:

- the production project (we currently deploy to `ppcway-509313` — confirm that
  is the one you want Claude enabled on), and
- whether we should create the staging project or you will. Creating one needs
  the **Project Creator** role (`roles/resourcemanager.projectCreator`) on the
  organisation or folder, which we do not have. If you would rather create it,
  name it and grant us access; if you would rather we did, grant that role.

Each project must have **billing enabled** before Claude can be turned on.

## 2. Check one thing about your billing account first

Google's documentation is explicit that if a **prohibited reseller** manages
your billing account, you will be *unable* to accept the terms or enable Claude
models at all. If your Google Cloud billing goes through a reseller rather than
directly to Google, please check this before anything else — it is the one item
on this page that could stop the plan rather than delay it.

## 3. Enable the API

The **Vertex AI API** (`aiplatform.googleapis.com`) must be on in each project.

Whoever does this needs the `serviceusage.services.enable` permission, which
comes with either:

- **Owner** (`roles/owner`), or
- **Service Usage Admin** (`roles/serviceusage.serviceUsageAdmin`).

## 4. Accept the terms, per model, per project

In the Google Cloud console: **Vertex AI → Model Garden**, open each Claude
model card, and click **Enable**. That button is where Anthropic's usage terms
are accepted. There is no separate document.

Three model cards, because we use three models for three jobs:

| Model | What it does for us | Why this one |
| --- | --- | --- |
| **Claude Sonnet 5.5** | Chat, the reason on each inbox card, the Monday letter | Everything a merchant reads |
| **Claude Haiku 5.5** | The jobs behind the screen: classifying, summarising, tidying | About a twentieth of Opus per token, and these run for every account every day |
| **Claude Opus 5.5** | Headlines and descriptions in the campaign builder | The one job where the words *are* the product |

Two things to watch while you are in there:

- **Note whether each model is offered in the United States multi-region.** We
  are configured for `us`, which is the setting your residency decision
  requires. If Haiku 5.5 is not available there, tell us and we will move the
  internal jobs onto Sonnet 5.5 — one line of configuration, and roughly a
  pound a month per account rather than a few pence. Nothing else changes.
- **A brand-new project usually starts with no Claude quota.** If the staging
  project comes up with zero, that is normal and we request an increase.

## 5. Two more services, smaller

- **Model Armor**, which screens what a merchant types before it reaches the
  model. Your brief requires it on every chat message, and we have built the
  code to **refuse to chat at all** if it is not configured — an unscreened
  chat box is worse than no chat box. This needs its own API enabled and a
  template created; we will send the exact template settings with phase 3.
- **Request-response logging.** This was an open item on your list — *on for 30
  days, or off*. **Our recommendation is on, for 30 days**, and it is also
  Anthropic's own published recommendation for Claude on Vertex, so that misuse
  can be found after the fact. It is separate from, and in addition to, the
  redacted prompt log we keep ourselves, which is already built and also keeps
  thirty days.

## What we have already done, so you can see where the line is

- The model service is built and tested. It calls Vertex AI in the **United
  States multi-region**, and it **refuses the global endpoint outright** rather
  than treating `global` as a shorter spelling of `us` — your brief says the
  global endpoint is not used, and the difference is which countries a prompt
  may be processed in. You asked whether blocking it needs an organisation
  policy: it does, and that needs the project to sit in a Cloud Organization,
  so until then the refusal lives in our code where it cannot be configured
  away by accident.
- There is **no Anthropic API key** anywhere in the deployment, and there
  should never be one. Authentication is Google's own, from the service
  account the container already runs as. Nothing for you to store or rotate.
- The model service **cannot reach your Google Ads credentials and cannot fetch
  a URL**, and a test reads the code's imports on every run to keep it that
  way.
- Our own **redacted prompt log** is built: thirty days, addresses and phone
  numbers and card-shaped numbers and tokens removed *before* the row is
  written, never on the way out.

## What we cannot start until you have done the above

Nothing, as it happens — the model service is finished and tested without
credentials, and the next phases (the mirror tables and the metric layer) do
not touch a model. So this is not blocking us this week. It becomes blocking
when the inbox cards need their reason sentences written, which is phase 1.2.

The thing that **is** blocking, and more urgently, is the `v0.1`
sub-documents. Your brief cites `v0.1 §1.1` to `§3.6` as the specification for
twelve of its sixteen phases, and only the brief itself arrived. Its own
technical-specifications section carried enough for phase 0 and most of the
guardrails, which is why work has continued; the rules R1–R5, the eight builder
steps and the per-campaign-type learning windows are named there but specified
nowhere we hold.
