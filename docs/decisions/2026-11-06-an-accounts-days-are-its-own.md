# An account's days are its own, not UTC's

**6 November 2026.** At the owner's request, after a new campaign's first day
appeared on the Campaigns page at an hour that made no sense to them.

## The decision

"Today" for an account's figures is the date in the account's own time zone,
as Google names it (`customer.time_zone`, for example "America/Toronto").
Every window still ends yesterday, as decided on 20 October, but it is the
account's yesterday:

- the screens: Home, Campaigns, Reports and the Otto chat's lookups;
- the nightly rules and the weekly email;
- the syncs: the hourly read asks Google for the account's today, and the
  nightly and first reads reach back from it.

The zone is kept on the connection. It is read when the account is chosen and
on every structure read, so existing connections have it within a quarter of
an hour of this shipping.

## Why

Google files an account's figures under dates in the account's zone, and its
own "last 30 days" ends at the account's yesterday. Ending at the UTC
yesterday turned the day over at 7 p.m. in Toronto and 5 a.m. in Karachi. It
also made the hourly read ask, in the evening west of UTC, for a day that had
not started in the account yet.

## What stays in UTC

Timestamps stay in UTC: when a figure was read, when a change was made. So do
PPCWay's own daily limits, the guardrails' changes per day and the operations
quota, which are counts of our activity rather than the account's calendar.
An account whose zone has not been read, or names a zone Python does not
know, is dated in UTC as before.
