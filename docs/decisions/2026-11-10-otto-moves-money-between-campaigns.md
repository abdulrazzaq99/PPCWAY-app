# Otto moves money between campaigns

**10 November 2026.** At the owner's request ("I am not getting any
recommendations from OTTO AI on any campaign, please check it, and make it
work").

## Why Otto was silent

The account counts nearly every click as a lead: 312 leads in 30 days, all
counted as forms, at 0.80 each. Otto had two rules:

- **R1** offers to exclude a search that spent at least the bar and brought
  no leads. When about every second click records a conversion, no search
  goes ten clicks without one, so R1 can never fire on this account.
- **R4** pauses ads Google has refused. There were none.

The campaigns did differ plainly. "PDFezy | Search" brought leads at about
0.40 each, while "pdfezy" paid about 2.69.

## Two rules of PPCWay's own

They compare a campaign with the rest of its own account rather than judging
one search, so they work on any account that counts leads at all.

| | R7, "a campaign whose leads cost far more" | R6, "a campaign held back by its budget" |
|---|---|---|
| When | Its leads cost at least **2×** what the rest of the account pays | Its leads cost at most **0.6×** the rest, and Google says it lost at least **20%** of its searches to its budget, on average over the last 14 days |
| Suggests | Lower its daily budget by **20%**, never below 1.00 | Raise its daily budget by **20%**, never past the account's daily budget ceiling |
| Risk | Low: spending less cannot cost more, though it can cost leads, and the card says so | Medium: more spend is always a person's decision, never applied unattended |

Both rules:

- look at the last 30 days;
- skip a campaign still learning, meaning under a week old or with less than
  a week of spend;
- skip a campaign on a shared budget, because changing it would move other
  campaigns' money too;
- skip any comparison resting on fewer than 10 leads on either side;
- stand down on an account that counts no enquiries, as R1 does.

The 20% step is the client's own band for a change a merchant may approve
alone. A bigger step would go to an expert.

These thresholds are judgements. They live on the rules in
`backend/src/ppcway/rules/catalogue.py`, and they stand until the client's R2,
R3 and R5 arrive.

## The ceiling

A budget rise needs a daily budget ceiling to measure against. The guardrails
already refused a rise without one, and nothing let a merchant set one.

- **Settings** now has "Budget ceiling for Otto": the most any one campaign
  may be suggested to spend in a day.
- **Saving it** writes a new version of the guardrail limits, never an edit,
  so past changes keep the limits that judged them.
- **Until it is set**, R6 offers nothing. The inbox, and that campaign's
  panel, say which campaign is waiting and why.

## Fixes found on the way

- **Guardrails.** The ceiling now governs rises only. A cut cannot breach a
  spending ceiling, and putting back the merchant's own earlier budget is not
  a new rise. Before this, both were refused when no ceiling was set, which
  would have left a merchant unable to spend less, or to undo a cut. A change
  whose direction is unknown is still treated as a rise.
- **The size of a change is now stored with each proposal.** The second
  ruling, at approval, reads it for the 20% and 50% bands, but it was never
  written. So a budget change would have passed those bands unmeasured.

## How the change reaches Google

- **The change.** A `set_budget` change updates the campaign budget's
  `amountMicros` with an explicit update mask, through the one door.
- **The undo.** It sends the previous amount back. Changes can be undone for
  30 days, as with every other change.
- **What the mirror keeps.** It now stores each campaign's budget resource
  name and whether the budget is shared, read on every structure sync. Both
  are kept out of the change fingerprint, so reading them for the first time
  is not reported as a change made in Google Ads.
