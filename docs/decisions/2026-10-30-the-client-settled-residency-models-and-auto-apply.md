# The client settled residency, the model route and auto-apply

**Date:** 30 October 2026
**Status:** accepted, by the client in writing

## What was decided

The client answered every decision that had been overdue since Friday 23
October, in a document titled *PPCway Otto — implementation brief for the
development team* and again in a written message the same day.

| Topic | Decision |
| --- | --- |
| Data residency | Not Canada-centric. US hosting is fine. The database stays on Neon, with no move to a Canadian region. |
| Model route | Claude on Google Cloud Vertex AI, US multi-region. Sonnet 5.5 for chat and explanations, Haiku 5.5 for internal jobs, Opus 5.5 for the campaign builder. No direct Anthropic API key. |
| Auto-apply | Owners may opt in from day one, off by default for new accounts. Negative keywords from wasteful search terms, and pausing disapproved ads, and nothing else. Behind a flag that stays off until the Terms and the Google filings are updated. |
| Approvals | Medium and high-risk changes always need a person. Approve-first stays the code default. |
| Privacy | The client rewrites the policy and collects fresh consent. Otto is pointed at no real customer account until they confirm consent is live. |
| Training on customer data | Not allowed. |
| Budget limits | Up to 20% on the normal route, 20–50% on the expert route, hard reject over 50% per change or 100% per day. |
| Keyword ideas | A model may suggest candidates only. Each must carry Keyword Planner volume before it can be added. |

## Why this is recorded here

Three of these reverse or retire earlier decisions in this directory and in the
delivery plan, and anyone reading those needs to find this.

- **Residency.** `2026-10-01-both-services-run-on-cloud-run-in-toronto.md`
  stands as a fact — both services still run in `northamerica-northeast2` —
  but it is no longer a *requirement*, and the report
  `reports/LLM choice for Otto AI chatbot.md` ends on a residency question that
  is now answered. No current frontier model processes data in Canada on any
  cloud; the recommendation in that report was contingent on the client
  accepting US processing, and they have.
- **The 20% versus 25% conflict** between the requirements and the blueprint is
  settled, and settled in a way that changes the shape of the guardrails rather
  than just a number: the limits are per plan, and a change between 20% and 50%
  must reach the expert route rather than be rejected before it gets there.
  `GuardrailConfig.max_change_pct` currently defaults to 25.0 and will need to
  become 20.0 with a second, higher expert threshold beside it.
- **Auto-apply** was the decision everything in weeks 3 and 4 was waiting on.
  It does not change the code default, which was already approve-first, but it
  does mean the consent record, the off switch and the kill switch are real
  work with a confirmed shape rather than a hypothesis.

## What the client still owes

Written down because the gates depend on it: the official contact address for
the legal pages, the rewritten privacy policy and confirmation that consent is
live, updated Terms, current pricing, a Google Ads consultant's review of a
week of cards, more connected live accounts, the per-industry templates and
blocked keyword lists, and the `v0.1` sub-documents the brief references by
section number throughout but did not attach.

That last one matters more than its position in the list suggests. The brief
cites `v0.1 §1.1` through `§3.6` as the specification for twelve of its sixteen
phases. Its own "Technical specifications" section reproduces enough to build
phase 0 and most of the guardrails, which is why work has started; the rules
R1–R5, the eight builder steps and the per-campaign-type learning windows are
named but not specified anywhere we hold.
