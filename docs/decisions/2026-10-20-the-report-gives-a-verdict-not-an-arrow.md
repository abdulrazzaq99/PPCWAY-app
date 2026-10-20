# The report gives a verdict, not an arrow

**20 October 2026.** Taken while building the reports screen.

## The decision

Every figure on the report carries one of four verdicts in plain words — **a
real change**, **within the normal range**, **too little data to tell**, or no
verdict at all — and the test behind it is named on the screen beside the
number.

## Why

Eleven leads last month and eight this month is not a thirty per cent collapse;
it is eleven and eight. A report that prints the arrow without the arithmetic
teaches a small business owner to panic on a Tuesday and spend money fixing
nothing. Most of the accounts PPCway serves have single-figure monthly lead
counts, where period-on-period noise is larger than almost any real effect.

## The tests

| Figure | Test | Why that one |
| --- | --- | --- |
| Leads | two Poisson counts: `(a−b)/√(a+b)` | Leads are counts of rare events, which is what Poisson describes |
| Lead rate | two-proportion z | A share of clicks, which is a proportion |
| Cost per lead | the leads' verdict | The spend is known; the lead count is the noisy part |
| Spend, clicks, click rate | none | See below |

Two standard errors is the threshold: a difference that size turns up by chance
less than about one time in twenty. Below ten leads across both periods, or a
hundred clicks across both, the answer is "nobody can tell", which is a result
rather than a failure.

## Why spend gets no verdict

Spend is a decision somebody made, not a measurement with noise in it. Asking
whether a budget change is statistically significant answers a question nobody
asked. The report says this in the definitions panel rather than leaving a
suspicious gap where an arrow would be.

## What this rules out

A dashboard full of green and red arrows, which is what every competitor ships
and what the client's own handoff drew. The figures are still coloured and the
change is still shown; what is not shown is a confident direction on a number
that cannot support one.
