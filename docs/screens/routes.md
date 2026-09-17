# Version 2 frames, by route

Every frame in `positions.tsv` and where it lives in `web/`. Drawn states are picked
with `?view=` until the backend drives them. Read the frame with the Figma plugin
(`get_node_info`, depth 7) before changing a screen.

## Sign-in (11 + 2)

| Frame | Route |
| --- | --- |
| 17:3588, 66:2 | `/login`, `/login?reason=signed-out` |
| 66:39, 87:8556, 17:3619, 17:3650, 17:3681, 17:3712, 90:15121 | `/signup`, `/verify-email`, `/invite`, `/forgot-password`, `/reset-password`, `/two-step` |
| 66:61, 66:81 | `/not-found`, `/error` |
| 89:14295 | `/login?brand=brightpath` |
| 90:15152 | `/two-step?view=setup` |

## Onboarding (27 + 5 audit + 1 resume)

| Step | Route and views |
| --- | --- |
| Account and plan | `/onboarding/account` |
| Connect Google Ads | `/onboarding/connect?view=connect,route,pick,accept,accept-choice,connected,queue,queue-full,existing` |
| Your business | `/onboarding/business?view=about,basics,money,sources,area,manual` |
| Website check | `/onboarding/website?view=running,report,finding` |
| Count your calls | `/onboarding/calls?view=number,verify,tag,sales,existing,quotes` |
| Review and launch | `/onboarding/review?view=writing,ready,backup,billing-done,live` |
| 87:8668 | `/onboarding/resume` |

## Overview (13 + 2 reports)

`/overview?view=` calls (17:1445), spend (92:16499), paused-everyone (87:5561),
support (76:2922), agency-view (89:13753), northgate (89:14118), week-one (81:2058),
disconnected (17:3295), suspended (81:2255), card-declined (89:13937),
no-tracking (87:5363), restaurant (87:8453), restricted (17:3483).
`/overview/reports?view=` report (67:608), dates (81:2437).

## Activity (12) and Approvals (1)

`/activity?view=` feed (17:1848), change (66:439), refused (87:4643),
outside-change (87:4821), headline-refused (87:4997), spike (87:5175),
calls-down (89:12926), weak-headlines (89:13357), alerts (17:3118),
emails (87:8030), batch (90:15752), switch-bidding (88:12203).
`/approvals` (17:1623).

## Campaigns (28) and Searches (1)

`/campaigns?view=` list (17:2236), detail (66:101), settings (80:657),
keywords (74:407), search-terms (79:162), ad-groups (79:2), ads (79:322),
account (87:6751), add-keywords (87:6199), write-ad (87:6490), assets (89:13533),
new (87:10926), website (87:5746), starter (87:5974), alerts (89:13120),
built (17:2048), searches-why (42:4772), ads-rules (42:4941), why-shape (42:5110),
pmax-logo (81:2827), pmax-month (92:16712), summit-plan (87:10317),
summit-list (87:10587), summit-leaks (88:11449), summit-month (88:11695),
summit-keywords (88:11952), summit-ad-test (88:12395), summit-results (88:12678).
`/searches` (66:270).

## Settings (19) and Help (1)

`/settings?view=` autonomy (17:2639), autonomy-early (90:14738), full-auto (67:1622),
plan (17:2816), team (67:1115), cancel (67:1284), delete (67:1453), business (74:644),
notifications (80:975), two-step (80:1256), switch-plan (80:1615),
payment-failed (81:1833), google (87:6993), results (87:7262), data (87:7528),
owner-only (87:7815), your-data (17:2967), add-ons (90:15292),
plan-owner-only (90:15930). `/help` (67:946).

## Agency (3)

`/agency/overview` (67:777), `/agency/clients/new` (87:8744), `/agency/settings` (81:3137).

## Internal admin (16)

`/admin?view=` list (17:2479), merchant (70:230), change-log (87:9604).
`/admin/jobs` (74:813), `/admin/errors` (76:1584), `/admin/quota` (82:3896),
`/admin/audit` (76:1811), `/admin/reviews?view=` categories (76:2256),
access (76:2084), block-list (87:9836). `/admin/staff` (76:2494),
`/admin/platform?view=` platform (76:2713), rules (90:15498).
`/admin/metrics?view=` metrics (82:4131), ai (87:11170). `/admin/runbook` (82:3550).

## Emails (14 frames, 28 emails)

`/emails?view=` monday (70:153), monday-special (87:9369), monday-stale (89:14430),
alerts (82:3472), sign-in (87:8974), team (87:9009), launch (87:9060),
problems (87:9103), money (87:9156), tracking (87:9210), privacy (87:9263),
category (89:14503), platform (87:9316), closed (89:14556).

## Report PDF (3)

`/reports/pdf?page=` 1 (87:9442), agency (87:9560), 2 (87:9493).

## Mobile (11)

The phone frames are the responsive form of the routes above, drawn into the app
shell (`components/app/shell.tsx`): 74:1459 login, 74:1054 overview, 74:1135
approvals, 74:1216 activity, 74:1297 campaign detail, 74:1378 card declined,
90:16087 reports, 90:16168 settings, 90:16249 billing, 87:8594 onboarding business,
87:8668 onboarding resume.

## Reference frames

92:17095 is the canvas index; 17:4106 is "States and motion", encoded in
`web/app/globals.css` and `components/ui/button.tsx`.

## Not from a frame

`/` is the public landing page (`web/components/landing/`), designed in code
on the Version 2 tokens. Every "Get a free audit" button goes to `/audit`
(`components/landing/audit-request.tsx`): name, email, phone, business name,
website and a consent tick, then a thank-you card. Nothing is stored yet; the
request is shown as sent until the audit endpoint exists. The photo in the "Nothing changes without your OK" band is a
seeded Picsum placeholder to be replaced with a real one.

`/audit/<id>` is the public report for one audit run: the two screenshots, the
eight checks, three more under the hood (first screen, site health, local
presence), what to fix first, and everything we saw
(`components/landing/audit-report.tsx`). It polls `/api/audit/<id>`, which the
Next.js route handlers forward to the backend's `/v1/audits/<id>`.

## Audit flow (added to Figma 16 September, built 17 September)

The frames are drawn in the old emerald; the screens use the blue brand like the rest.

| Frame | Screen | Route |
|---|---|---|
| 181:5823 | Find your business, and the three matches | `/audit`, `/audit?view=results` |
| 181:5880 | Confirm your listing | `/audit?view=confirm` |
| 181:5920 | Checking | `/audit?view=checking` (static); `/audit/<id>` while a real run is in progress |
| 181:5971 | We could not find you | `/audit?view=not-found` (the form starts a real run when a website is given) |
| 181:6011 | Report, already advertising | `/audit/report?view=advertising` |
| 181:6215 | Report, not advertising yet | `/audit/report?view=fresh` |
| 181:6419 | Mobile audit report | the report pages at phone width |
| 181:6555, 181:6981 | Marketing landing page | `/` was designed in code before these frames existed; not redrawn |
| 179:4047 | Index | replaces 92:17095 |

The live report at `/audit/<id>` still uses the eight-checks layout until the listing,
ads and competition data exist to fill the frame's four panels.
