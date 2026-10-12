# The Developer Requirements, mapped against what exists

**12 October 2026.** Read against `Requirements.pdf` (PPCway Dashboard Developer
Requirements, 6 October 2026, 16 pages).

## The short version

The requirements describe four delivery phases. We are **most of the way through
phase 1 and a quarter into phase 2. Phases 3 and 4 have not been started.**

What exists is real and deployed: the free audit, Google sign-in, a live Google
Ads connection reading five reports from a merchant's own account, Keyword
Planner volumes, a domain, and Basic API access granted today.

What does not exist is the part the product is named for: **nothing writes to
Google Ads.** There is no proposed change, no approval, no guardrail, no undo,
no Otto, no expert console, no plans, no billing, no local mirror of an account.

One caution when judging progress by looking at the app. There are 47 screens in
`web/app`. **Eleven are wired to the backend; the other thirty-six are Figma
states drawn with sample data** (reachable at `?view=`). Campaigns, approvals,
activity, searches, settings and the whole admin and agency area look finished
and do nothing. That was a deliberate decision — design first, then implement —
but it makes the app look several phases further along than it is.

## Phase by phase

| Phase | Requirement's scope | State |
|---|---|---|
| 1. Foundation | Auth, organisations and roles, secrets, real Google Ads connection through the gateway, Basic access, sync and local mirror | **~70%**. Auth, secrets, connection and Basic access done. Organisations, roles and the local mirror are missing. |
| 2. Read and recommend | Dashboard home, campaign list and detail, reporting, baseline audit, Otto recommendations shown but not applied | **~25%**. The audit is done and exceeds what was asked. Campaign list and detail, reporting and Otto are not built. |
| 3. Approve and write | Proposed changes, approvals, guardrails, undo, editing campaigns, expert console | **0%**. |
| 4. New advertisers | Account creation under the manager account, billing deep link, campaign builder, learning mode, Standard access with RMF | **0%**. |

Phase 1's exit gate — five internal accounts connected and synced for seven days
with no data mismatches — cannot be met yet, because there is no sync.

## Section by section

### Onboarding and account connection

| Requirement | State |
|---|---|
| Sign-up, email or Google, audit details carry over | **Partly.** Google sign-in works; an audit run signed out is claimed into the account afterwards. Email and password sign-up is drawn only — there is no password endpoint in the backend. Email verification does not exist. |
| Path A, new to Google Ads: account created under the PPCway manager | **Not started.** No manager account, no `createCustomerClient`, no billing deep link. |
| Path B, existing account: Google sign-in, pick accounts, manager link | **Mostly.** OAuth with the `adwords` scope, account listing and a picker all work and are deployed. **Manager-link requests are not built** — we read the merchant's account by their direct grant, not through a manager link. |
| First sync: structure and 90 days of performance, baseline audit, first three recommendations in 5 minutes | **Partly.** The audit runs in about a minute and reads five account reports live. There is no import, no 90-day history, no stored mirror, and no recommendations. |
| Conversion tracking check | **Partly.** The public audit detects tracking on the website. The account-level `conversion_action` check and the guided setup are not built. |
| Expert match | **Not started.** |
| Disconnect, tokens deleted | **Partly.** The model supports revocation (`revoked_at`) and the code honours it; there is no screen to do it. |

### New advertiser: campaign builder

**Not started.** All eight steps exist as drawn onboarding screens with sample
data. Nothing is wired, and nothing can be created in Google Ads.

### Existing advertiser: campaign management

**Not started.** `/campaigns` is a drawn state. There is no campaign mirror
table, no edits, no edit flow, no external-change detection, no bulk actions.

### Dashboard home and reporting

| Requirement | State |
|---|---|
| Results strip (leads, cost per lead, spend against budget) | **Not built.** The signed-in home shows the latest audit and a connect panel. |
| Needs you | **Not built.** |
| Otto activity | **Not built.** |
| Visibility Score over time | **Partly.** Each run has a score; there is no history chart and no series. |
| Your expert | **Not built.** |
| Reports: weekly email, monthly PDF, white label | **Not built.** No email is sent by the backend at all. |
| Default metrics at every level, plus search terms view | **Partly.** Search terms, keywords, impression share and policy status are read for the connected account and shown in the report. They are not browsable per campaign or ad group. |

### Website audit — the strongest part

**Done, and past what was asked.** Fourteen public checks across the Google
listing, the website and the competition, with a real crawler, a headless
browser, a live mobile speed test, conversion-tracking detection, trust signals
and policy checks. Plus four account-level checks from the merchant's own Google
Ads, and the money line from Keyword Planner.

Missing from this section: it does not re-run on a schedule or on change
detection, there is no history chart, no "what changed since last time", no
alerts, no per-page landing view, no "send to my web person", and it does not
yet live under a Free tools area in the dashboard.

### Otto recommendations, approvals and guardrails

**Not started**, and this is the heart of phase 3. None of the risk routes, the
spend caps, the learning-window rule, undo, explainability or thresholds exist.
No language model is wired into the backend at all.

### Expert in the loop

**Not started.** No console, no sign-off, no sessions, no hours.

### Roles, plans and limits

**Not started.** No organisation, no membership, no roles, no plans, no price
book, no spend warnings. Everything today is one person with one account.

### Data model

Six of the eleven entities exist:

| Entity | State |
|---|---|
| Organization | missing |
| User and Membership | partly — `account` and `account_session`; no organisation, no role |
| Business profile | partly — held on `audit_request`, not a profile of its own |
| Ads connection | **done** (`ads_connection`, encrypted refresh token, chosen customer) |
| Campaign mirror | missing |
| Performance facts | missing |
| Proposed change | missing |
| Applied change | missing |
| Guardrail policy | missing |
| Audit run | **done** (`audit_request`, `audit_run`) |
| Expert task and time entry | missing |

### Integrations

| Integration | State |
|---|---|
| Google Ads API | **done for reads** through one service. No writes, no batch mutates, no queue. |
| Google sign-in (OAuth) | **done**, tokens encrypted with a managed key |
| Business listing and places | **done** |
| Site checks | **done** |
| Language model | **not wired** |
| Billing | **not wired** |
| Email | **not wired** |
| Scheduling | **not wired** |
| Product analytics | **not wired** |

### Google Ads API access and compliance

| Requirement | State |
|---|---|
| Basic access | **granted, 12 October** |
| Standard access | not applied for. Required before serving real customers at scale. Review is 10–15 business days. |
| RMF features | not built. Applies at Standard access, and a failed audit carries fees. Target ROAS bidding and the search terms view must ship even though launch customers will not need them. |
| One production manager account owning API access | **not created.** API access is on our Cloud project; there is no PPCway manager account, which phase 4 needs for creating customer accounts. |

### Non-functional

| Requirement | State |
|---|---|
| Security: secrets in a manager, encrypted tokens, least privilege | **mostly done.** Secret Manager, Fernet, one service holding credentials. No MFA for staff, no audit log of sign-ins. |
| Sync every 15 minutes / hourly / nightly | **not built** |
| API quota: write queue, retries, backoff, 80% alerts | **not built** (no writes yet) |
| Reliability: no half-applied change | **not applicable yet** |
| Performance: home under 2 seconds from the mirror | **not measurable** — no mirror; the home does fetch rather than render from local data |
| Privacy: DPA, residency, deletion within 30 days | **partly.** Privacy policy and terms published; Toronto residency chosen and recorded; deletion is by email request, not automated. |
| Accessibility: WCAG 2.2 AA | **unverified.** No audit has been run. |
| Localisation: currency, time zone, 12 languages | **not built.** Currency is read from the account and displayed; everything else is English only. |
| Mobile | **partly.** Public pages and the report are responsive; the drawn app screens were designed desktop-first. |
| Observability: structured logs, traces, status page | **partly.** Structured logs and Cloud Run metrics; no traces, no status page. |

## What I would build next, in order

1. **Organisations, memberships and roles.** Everything else hangs off it — plans,
   agency accounts, expert access, who may approve. It is small and it is
   blocking.
2. **The local mirror and sync.** Campaign, ad group, keyword, ad and daily
   performance facts, with a scheduled sync. Phase 1's exit gate needs it, the
   dashboard's 2-second load needs it, and every phase 2 screen reads from it.
3. **Dashboard home for real** — results strip, needs you — reading the mirror.
   This replaces the largest drawn screen with a working one.
4. **The change pipeline**: proposed change, applied change, guardrail policy,
   undo. Build it before anything that writes, so the first write already passes
   through it. This is Blueprint §5.5 and the client's "nothing changes without
   a decision".
5. **Otto**, once the pipeline exists, starting with the two cheapest and safest
   recommendations: negative keywords from wasteful search terms, and pausing a
   disapproved ad. Both are low risk in the requirement's own table.
6. **Standard access and the manager account**, in parallel with 4 and 5, because
   the review takes weeks and phase 4 cannot start without them.

## Open questions in the document that block work

The requirements list eight. Three of them block the next two items of work and
need the client's answer before building:

- **Which change types may auto-apply by default, and is auto-apply on or off for
  new accounts?** Decides the default guardrail policy.
- **Campaign limits for Growth and Agency**, and what happens when spend passes
  the plan limit. Decides the plan model.
- **Data residency: one region or three?** We chose Toronto on 1 October. If the
  answer is "US and EU too", that decision reopens and the deployment changes.

The other five — trial or first-month charge, expert turnaround and weekend
cover, which campaign types follow Search, white-label domain timing — can be
answered later without blocking.
