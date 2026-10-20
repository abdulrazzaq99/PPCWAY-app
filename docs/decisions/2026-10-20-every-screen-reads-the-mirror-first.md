# Every screen reads the mirror first, and Google only to fill a gap

**20 October 2026.** Taken while building week two of the four-week plan.

## The decision

The dashboard, campaigns and reports read `ads_campaign_day` and the mirror
tables. Google is asked only in two cases:

- the mirror holds nothing yet, which lasts from connecting an account until the
  first sync finishes;
- a campaign's per-keyword and per-ad performance and its search terms, which
  the mirror does not hold, read live and merged over the mirror's structure.

## Why

Four GAQL round trips to California on every page load is what made the
requirements' two-second dashboard unreachable. It also made the question the
client's design asks on every screen — *and how does that compare with before?*
— unaffordable, because answering it doubles the reads.

Reading our own database makes the comparison free. The home screen now answers
this period, the period before it, the month to date, a day-by-day series for
the account and another per campaign row in one pass over one table. The report
adds the same period a year ago for the cost of two more queries.

## The two judgements inside it

**The window ends yesterday.** "Last 30 days" means the thirty days up to and
including yesterday, which is what Google's own `LAST_30_DAYS` means. A merchant
holding our screen beside the Google Ads interface sees one number, not two.
Today is still mirrored hourly; it is simply not in that sum.

**A campaign that has gone from Google still counts what it spent.** It is
listed, marked gone, and left in the totals, because a figure that quietly drops
it cannot be reconciled against a bank statement.

## What this costs

Freshness, bounded and stated. Every screen that shows a figure from the mirror
also says when we last read the account, because a number from a database owes
the reader its age. Structure syncs every fifteen minutes, today's numbers
hourly, and the previous three days are rewritten nightly because conversions
arrive late.

## What is deliberately still live

Per-keyword performance and search terms. Mirroring them means a keyword-day and
a search-term table, and the week-three recommendation engine is what actually
needs them — wasteful search terms and weak keywords are two of its five
proposal types. Building those tables now and again for Otto would be building
them twice, so campaign detail merges Google's reporting over our structure
until week three, and says which half it could not read when Google refuses.
