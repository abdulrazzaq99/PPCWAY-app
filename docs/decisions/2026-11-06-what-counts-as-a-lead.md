# What counts as a lead: page views do not

**6 November 2026.** Approved by the owner. Otto had found nothing to suggest on
the PDFezy account, and the cause was in what PPCWay counted as a lead.

## What was wrong

Google Ads counts whatever an account tells it to count as a conversion, and
some accounts count a page loading. PDFezy's new campaign showed 38 clicks and
38 leads. PPCWay counted every conversion that was not a call as a form, page
views included, which caused two problems:

- **The figures were wrong.** Every lead count and cost per lead on screen was
  really a count of visits.
- **R1 could never fire.** R1 only offers to exclude a search that brought no
  leads. When every click is a lead, no search with a click ever has zero.

## The rule now

A conversion is a lead unless its category is something a visitor does on the
way. Seven categories are not leads, in Google's own words: `PAGE_VIEW`,
`ENGAGEMENT`, `ADD_TO_CART`, `BEGIN_CHECKOUT`, `STORE_VISIT`,
`YOUTUBE_FOLLOW_ON_VIEWS` and `IN_APP_AD_REVENUE`. Everything else counts:

- forms, calls, sign-ups, quote requests and bookings;
- sales, because a search that sells is never wasted;
- `DEFAULT` ("Other"), where a real enquiry form often lands when its category
  was never set.

The list names what does *not* count rather than what does. That way a doubtful
category counts. Leaving it out could make a search that brings enquiries look
wasted, and offering to stop such a search is the worst mistake Otto can make.
Doubt therefore costs a missed suggestion, never a wrong one. The definition
lives in `backend/src/ppcway/ads/leads.py` and nowhere else.

## Where it applies

- **The day mirror.** Calls and forms are leads, and the new `not_leads` column
  holds page views and the like.
- **The search-term mirror.** A new `leads` column holds the conversions that
  were leads. R1 reads that column, falling back to all conversions where a day
  was not split, which can only make it propose less.
- **The live campaign tabs.** The keywords and searches use the same split, so
  the "waste" mark in the search-terms tab agrees with R1.
- **The live home-screen fallback, Otto's search-term tool and the audit's
  wasted-search finding.**

Google will not report the conversion category in the same query as clicks,
cost or impressions. So every read that needs leads asks a second question for
the split.

## Two guards

1. **An account that counts no enquiries gets no exclusions.** Such an account
   has spent money in the last 30 days without counting a single call, form,
   sign-up or sale. On it, every search looks wasted, and the busiest look the
   most wasted. R1 stands down there, and the inbox and the campaign panel say
   why in plain words. R4 still runs, because a refused ad is a fact from
   Google. The audit says the same instead of listing the account's best
   searches as waste.
2. **History heals itself.** Days stored before this change have `not_leads`
   empty. The nightly backfill normally re-reads three days. While any day in
   the 90-day window is still empty, it re-reads the whole window, searches
   included, then goes back to three days.

## Not decided here

- **Per-industry lead definitions,** for example whether a download is a lead
  for a software merchant. That waits on the client's per-industry rules.
- **Keyword days** (`ads_keyword_day`) still hold all conversions. No
  implemented rule reads them yet; R2 and R3 will need the same split when they
  are specified.
