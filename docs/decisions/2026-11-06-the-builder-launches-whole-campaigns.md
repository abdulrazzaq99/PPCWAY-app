# The campaign builder launches whole campaigns

**6 November 2026.** At the owner's request. "New campaign" led to a 404, and
the builder only knew how to create keywords, because the client's eight
builder steps (`v0.1 §3.2`) were never supplied. The flow follows the
designs instead: "Start a new campaign" (Figma 87:10926) and "Here's the
campaign we built for you" (17:2048).

## The flow

1. **The merchant says what it is about.** That covers the services (up to
   five, each becoming an ad group), where it shows (countries, regions or
   cities, picked from Google's own list), the language, the daily budget, how
   Google bids, the landing page, what the ads may claim, and which searches
   never to pay for.
2. **PPCWay writes it.** For each service, Keyword Planner's ideas for those
   places and that language are taken, kept only if they contain every word of
   the service and Google says people search for them. Then fifteen headlines
   and four descriptions are drafted by the model, and each line passes the
   six checks against what the merchant said the business does. Nothing is
   written to Google.
3. **The merchant reviews and edits it.** Keywords can be taken out but never
   typed in; only Keyword Planner may add one. Edited ad text goes through the
   same checks. The merchant must confirm the campaign is not EU political
   advertising, because Google requires that declaration on every new
   campaign.
4. **Launch.** It needs owner, admin or expert access. The write switch and
   the stops are read at that moment, and the operations are counted against
   the day's quota. Google then checks the whole campaign without creating
   anything, and only then is it created.

## Choices made

- **One request, all or nothing.** The budget, campaign, places, language,
  excluded searches, ad groups, keywords and ads go to Google's account-wide
  mutate as one request, linked by temporary ids. Google applies all of it or
  none, so there is nothing to roll back. The brief asked for rollback because
  a launch sent in pieces can half-land; one request cannot.
- **Search only.** Google Search, no partners, no display network. Ads show to
  people in the places chosen, not merely interested in them. Keywords are
  phrase match: a search has to carry the keyword's meaning, so a new campaign
  does not pay for the loose matches broad match allows.
- **Bidding is the merchant's choice:** most clicks (the default, needing no
  history) or most leads (once conversions are counted properly).
- **No AI declaration on the ad.** The brief asked for
  `synthetic_content_info`, but Google accepts it only on image and HTML5
  ads, and a responsive search ad that carries it is refused. Checked against
  the v25 definitions. The disclosure is PPCWay's own instead, on the review
  screen and in the success message.
- **A launch is the merchant's, not an automated change.** The guardrails'
  weekly cap and spend ceilings, which govern what Otto proposes, do not
  decide it. The write switch and the stops still do, because "stop every
  write" has to mean every write.
- **The draft is the record.** `campaign_draft` keeps the plan, who launched
  it and when, and what Google created or why it refused.

## Not yet

- Adding a keyword by hand, which would have to be checked against Keyword
  Planner first.
- The client's per-industry prohibited claims and category templates. Until
  then, a theme whose ad text keeps failing the checks says so instead of
  falling back to a template.
- Plan limits on how many campaigns a business may run, which wait on pricing.
