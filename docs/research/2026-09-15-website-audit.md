# The website audit: how we run it, what others offer, where our edge is

Research note, 15 September 2026. Uncommitted draft for the owner to read before
the backend is designed. Sources are listed at the end.

## 1. What the audit has to be

The audit already exists on the surface: eight checks on the landing page and in
onboarding step 4, a six-field request form at `/audit`, and the promise "eight
checks, one working day, we change nothing on your site". The backend does not
exist. The proof of concept has a crawler (httpx and selectolax, robots-aware,
SSRF-safe, 25 pages, 60 seconds) that extracts business facts for ad copy, and a
policy validator that checks ad copy against the crawled page. It has no page
speed, no tag detection, no headless browser, and it deletes `<script>` before
reading, so it throws away the very evidence three of the eight checks need.

The Blueprint (section 6.2) already specifies the shape: static fetch first,
escalate to headless Chromium when the static parse is thin, PageSpeed Insights
for Core Web Vitals, quality signals stored in a `page_speed_signals` column,
raw HTML kept 30 days, and a disclosure at the point of crawl that site content
goes to Anthropic. The handoff (section 6) records the agency research: a
website audit covers measurement and tags, speed, message match, conversion
path, trust signals, policy risk and business facts, with tracking validated
before anything else and findings ranked by money at stake.

So the research question is not "what should the audit check". That is decided.
It is "how do we perform each check well, what do others do, and where can we be
better than them".

## 2. What agencies and tools actually offer

Three families exist. None of them is what we are building.

**Account graders.** WordStream's Google Ads Performance Grader and Adalysis's
free audit connect to an existing Google Ads account by OAuth and score Quality
Score distribution, wasted spend, impression share, account activity and
structure, in minutes. They need an account with history. They tell you nothing
about the website beyond Quality Score's landing page column. Their purpose is
lead capture for the paid tool.

**Agency "free audits".** Canadian agencies (IT Cares, AMS, Third Marble and
dozens more) ask for view access to the account and a screen-share call. A
strategist reviews structure, spend, tracking and landing pages and sends a
prioritised fix list, then pitches management from about $600 a month. The
audit is a sales call. It takes days, it needs an account, and the findings are
in agency language.

**Landing page graders.** Leadpages, Unbounce, Web Anatomy, Adamigo, LandingScore
and similar take a URL and return a 0 to 100 score across speed, SEO tags,
mobile, copy clarity, trust elements, form friction and tracking tags. They are
generic conversion-rate tools: the same rules for a SaaS signup page and a
plumber. They do not know what the ads will say, what people search for near the
business, or whether a call can be counted. Several are now "AI readiness"
pitches.

What every one of them shares: a score, not a decision; a page, not a business;
a one-off, not a watch.

## 3. The eight checks, and how each is performed

Confidence is how sure the automated result can be without a person. "Needs a
question" means the honest answer is to ask the merchant one thing rather than
guess.

| Check on the page | How we run it | Source of truth | Confidence |
|---|---|---|---|
| Counting calls and forms | Headless Chromium loads the page, records every network request and the `dataLayer`. Look for a Google tag (`G-`, `AW-`, `GTM-`), an Ads conversion or remarketing hit to `googleads.g.doubleclick.net`, a GA4 hit to `/g/collect`, and a call tracking script (CallRail `swap.js`, WhatConverts, CallTrackingMetrics, Ringba). Presence is not enough: we report whether a tag fired on load. | Observed requests | High for presence and firing. Whether a call is counted as a conversion needs the account or a question. |
| Speed on a phone | PageSpeed Insights API, mobile strategy: Lighthouse LCP, CLS, INP, page weight, render-blocking resources. Field data from CrUX when the site has enough traffic, which most small sites do not, so we say "simulated 4G, mid-range phone" in the report. | PSI API | High. It is Google's own number. |
| Works on a phone | Lighthouse viewport, font size and tap-target audits from the same PSI call, plus our own headless render at 390px: horizontal overflow, a visible phone number in the first screen, and whether it is a `tel:` link. | PSI plus our render | High |
| Page matches the ad | Keyword Planner `generateKeywordIdeas` with the site URL and the merchant's city as seeds gives what people near them actually search. Group into themes (the same step the campaign uses), then check whether each theme has a page whose headline and body carry it. The PoC validator's landing page consistency check already does the reverse direction. | Google Ads API plus crawl | Medium. Themes are good; "which page fits" needs judgement, so the report names the gap and the campaign step confirms. |
| Contact form | Detect forms and their provider (Gravity, WPForms, HubSpot, Jotform, Wix, Squarespace). Detect a thank-you page from links, sitemap and common paths. We never submit a form on a client's site. If the thank-you page cannot be seen from outside, the finding says "Needs you" with one question, exactly as the drawn "one finding" screen shows. | Crawl plus render | Medium. Presence high; thank-you flow often needs a question. |
| Google's tags | Same headless pass: Tag Manager container, GA4 measurement ID, Ads conversion ID, and Consent Mode default state in the `dataLayer`. | Observed | High |
| Trust signals | JSON-LD LocalBusiness (address, telephone, openingHours), visible address and hours, licence numbers by trade pattern (TSSA, ECRA/ESA, HRAI, college registration for dentists), review widgets, privacy policy page. Optional: Google Places lookup for the business's rating and review count, and a name-address-phone match between site and profile. | Crawl plus Places | High for presence. |
| Words Google may object to | Run the existing validator lexicons (superlatives, guarantees, "best", "#1", health and financial claims, trademarks, price claims) over the crawled page text instead of ad copy. Add the Destination Requirements list: broken links, pop-ups, download links, insufficient content. Finding is phrased as "we keep this out of your ads", not "change your site", unless it is a destination policy risk. | Validator plus policy list | High for lexicon hits. |

Two checks the running screen shows and the report folds in are already built in
the PoC and port as they are: "Pages we can read" (robots, page count,
`SOURCE_INSUFFICIENT`) and "Your phone number" (JSON-LD, microdata, `tel:`,
pattern).

Safety check that costs nothing: Google's Web Risk API (the commercial Safe
Browsing) tells us whether the site is flagged for malware or phishing, which
would get every ad disapproved. Worth a ninth silent check that only surfaces if
it fails.

## 4. Where the edge is

Ranked by how much it matters to a plumber deciding whether to trust us.

1. **No account needed, and it is the first step of the product, not a trap.**
   Every grader needs a Google Ads account with history. Our market has never
   advertised. The audit runs from a URL, and the same engine and record carry
   straight into onboarding step 4, so nothing is re-done when they sign up.
2. **We check whether a call can be counted, not whether a tag exists.** Tag
   graders look for a script. We watch it fire, we look for call tracking, and
   we refuse to launch without an observed conversion (Blueprint 13.5). No
   competitor ties the audit to the launch gate.
3. **Findings ranked by money, in plain words.** Each finding carries an
   estimate from Keyword Planner: average cost per click and volume for the
   business's own themes in its own city. "Without call counting, about $X a
   month of ad spend can't be judged" lands harder than "conversion tracking
   missing". The handoff research says agencies rank by money at stake and
   graders do not.
4. **"What people near you search for" inside the audit.** The Keyword Planner
   pass gives a preview that no landing page grader can: the real search terms
   and rough monthly volume for their trade and town. It is the strongest
   hook on the report and costs one API call.
5. **Trade-aware trust signals.** Licence formats, review platforms and
   restricted-category rules per trade (HVAC, plumbing, electrical, dental,
   legal). Generic graders check "social proof present".
6. **A watch, not a one-off.** Re-run the audit monthly and after any campaign
   change. A site that loses its tag or breaks its form pauses spend and raises
   an approval, through the same guardrail order every change follows. Agencies
   audit once; graders never come back.
7. **Canada-specific.** Quebec Law 25 needs opt-in consent before tags load, so
   Consent Mode state matters; PIPEDA elsewhere. We read the consent default
   from the `dataLayer` and say what it means for counting.
8. **Honesty on limits.** We say "simulated 4G" when there is no field data, we
   never submit their form, and where a check cannot be seen from outside the
   report asks one question instead of guessing. Graders present a score as
   truth.

## 5. Costs, quotas and limits to plan for

- PageSpeed Insights API: free, 25,000 queries a day and 400 per 100 seconds per
  key. No paid tier. One audit is two calls (mobile and desktop) at most.
- Google Ads API keyword ideas: within the existing developer token; planning
  requests count against the daily operations quota, one or two per audit.
- Web Risk API: free tier, then pay as you go. Safe Browsing v4 is
  non-commercial only, so use Web Risk.
- Google Places API (New) for the profile match: paid per Place Details call,
  cents per audit. Optional in phase one.
- Headless Chromium: one worker container on the isolated `worker-crawler` queue
  with the same SSRF pinning, 30 to 60 seconds per site, memory bounded.
- CrUX field data is absent for most small sites. Do not promise "real user"
  speed.
- Google's Mobile-Friendly Test API was retired in December 2023. Lighthouse
  audits in PSI are the replacement.
- Raw HTML kept 30 days, extracted findings for the account's life, the
  disclosure that content goes to Anthropic shown at the point of crawl.

## 6. Proposed pipeline

One job, six stages, each writing its result so a partial audit still reports.

1. **Safe fetch.** Port the PoC crawler as it is: robots, SSRF pinning, 25
   pages, 60 seconds. Keep raw HTML this time, and stop stripping scripts before
   the tag pass.
2. **Render.** Headless Chromium on the home page and the top service and
   contact pages: network log, `dataLayer`, 390px screenshot, overflow check.
   Also the escalation path when the static parse is thin.
3. **Measure.** PSI mobile and desktop for the home page and one service page.
4. **Understand.** Keyword ideas by URL and city, grouped into themes; message
   match per theme; trust and licence extraction; policy lexicons over page
   text.
5. **Rank.** Attach a money estimate and a status (Good, Needs you, We'll
   handle it) to each finding, ordered by money.
6. **Deliver.** For a signed-in merchant, the report view in step 4. For an
   `/audit` lead, a report link by email within one working day, with an
   optional human glance before it goes, then the same record becomes step 4
   when they sign up.

The audit record is `audit(site, requested_by, checks jsonb, findings jsonb,
page_speed_signals jsonb, raw_html_ref, completed_at)` and a monthly re-run
feeds the guardrail pipeline.

## 7. Effort

The Blueprint sized the crawler with PageSpeed at 11 days and the tracking
assistant at 12. Adding the headless pass, tag and call tracking detection, form
and thank-you detection, the keyword-ideas message match, policy over page text,
the money ranking and the lead email is roughly 18 to 22 working days for one
engineer, in this order: fetch and render, tags, speed and mobile, trust and
policy, message match and money, delivery and the monthly watch.

## 8. Decisions for the owner

1. Approve the eight checks as the contract, with the ninth silent safety check.
2. Approve one working day with a human glance for `/audit` leads, or instant
   delivery with no glance.
3. Approve Places lookup (paid, cents) in phase one or defer it.
4. Confirm the money estimate wording is allowed on a public report before an
   account exists.
5. Confirm the monthly re-run is in scope for launch.

## Sources

- Google Ads Destination requirements policy: https://support.google.com/adspolicy/answer/6368661
- Google Ads landing pages report: https://support.google.com/google-ads/answer/7543502
- PageSpeed Insights API: https://developers.google.com/speed/docs/insights/v5/get-started and https://developers.google.com/speed/docs/insights/v5/about
- PSI quota discussion: https://groups.google.com/g/pagespeed-insights-discuss/c/dB7hWmGAGsw and https://bjb.dev/log/20221009-pagespeed-api/
- Mobile-Friendly Test retirement: https://searchengineland.com/google-officially-drops-mobile-usability-report-mobile-friendly-test-tool-and-mobile-friendly-test-api-435377
- Keyword ideas by URL: https://developers.google.com/google-ads/api/rest/reference/rest/v18/customers/generateKeywordIdeas
- Phone call conversion tracking: https://support.google.com/google-ads/answer/6100664 and https://support.google.com/google-ads/answer/2382961
- CallRail dynamic number insertion: https://support.callrail.com/hc/en-us/articles/5711814948877-Dynamic-number-insertion-overview
- Web Risk vs Safe Browsing: https://developers.google.com/safe-browsing/v4/usage-limits and https://cloud.google.com/security/products/web-risk
- Adalysis free audit: https://adalysis.com/free-ppc-audit/
- WordStream grader: https://www.wordstream.com/google-adwords and https://paceads.com/blog/google-ads-grader-tools-compared
- Landing page graders compared: https://www.landingscore.app/blog/best-free-landing-page-audit-tools and https://leadpages.com/tools/landing-page-analyzer
- PPC audit checklists: https://www.trackingplan.com/blog/ppc-audit-checklist and https://upp.ai/resources/ppc-audit-checklist
- Quality Score and landing page experience: https://support.google.com/google-ads/answer/6167118 and https://www.groas.com/post/google-ads-quality-score-optimization-2026-improve-expected-ctr-ad-relevance-landing-page
- Canadian consent: https://www.cookie-banner.ca/blog/cookie-consent-canada-guide-2026 and https://cookiebeam.com/guides/quebec-law-25-cookie-consent-2026
- Local business schema and trust: https://searchengineland.com/schema-local-visibility-google-ai-470906
- Home services PPC landing pages: https://www.plumberseo.net/ppc-landing-pages-that-convert-for-plumbing-services/
- Agency free audits in Canada: https://itcares.ca/en/google-ads-services-canada.html and https://www.thirdmarblemarketing.com/disp-camp-google-ads-audit
- Internal: `docs/handoff/2026-09-15-poc-handoff.md` section 6, Blueprint sections 4.4, 6.1, 6.2, 13.5 and 13.7, PoC `src/ppcway/crawler/` and `src/ppcway/validator/`.
