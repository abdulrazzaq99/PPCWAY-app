# Both services keep one instance running

**12 October 2026.** Prompted by "why does the site go down after a while".

## What was happening

Nothing was down. Both Cloud Run services scaled to zero when idle, so the first
visit after a quiet spell paid for a container to boot — and because the web
page fetches the API on the server, the visitor paid for **two** cold starts in
a row. Measured: the API's health check took 9.9 seconds, pages 1.8 to 3.3.

It never showed up in a check, because any check warms the thing it is checking.
That is the trap: by the time anyone looks, it is fast again, so the report is
"it goes down sometimes" and the logs say everything is fine. They were fine.

## What changed

`--min-instances=1` and `--cpu-boost` on both services. Afterwards: the API
answers in 0.9 seconds, pages in 1.1 to 1.8.

## What it costs, and why the API is the expensive half

An always-warm instance is billed whether anyone visits or not. The web service
is cheap. The API is not, because its CPU is permanently allocated — a decision
taken so an audit keeps running in the background after the response is sent,
and the reason that flag exists at all. Expect roughly $25 to $60 a month.

If that is not worth paying before launch, the middle option is to keep only the
web service warm. Most of the felt improvement, a fraction of the cost, and the
API cold-starts on the first page load after a quiet period.

## What would make this unnecessary

The local mirror, in week two of the delivery plan. Once the dashboard reads our
own database instead of calling Google through the API on every page, the web
service stops depending on a second cold start, and keeping the API warm matters
only for audits people are actively waiting on.
