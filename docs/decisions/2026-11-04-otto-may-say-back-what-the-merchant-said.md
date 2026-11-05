# Otto may say back the numbers the merchant typed

**4 November 2026.** Taken while fixing what the owner's run of the Otto test
script found.

## The decision

The number check still refuses any number Otto works out for itself. It now
accepts, besides the figures this turn's lookups returned:

- every other number those lookups put in front of the model: the period
  before, calls and forms, the window's dates, and numbers written as words in
  our own help text ("put back for thirty days");
- the numbers the merchant typed in this conversation: "in 2019", "the last
  twelve months", "$500".

It does not accept the numbers in Otto's own earlier answers. The system prompt
already has a figure looked up again rather than carried over, and the check
holds to that.

## Why

The brief's rule is "every number matched to that turn's tool results; one
rewrite, then a fixed template". Read narrowly, a merchant who asked for their
cost per lead in 2019 could not be told "I cannot see 2019", because no lookup
returned 2019. That is what happened: the rewrite could not fix what was not
wrong, and the merchant got the fixed fallback. The same happened to "how do I
undo a change Otto made?" and to a question about the last twelve months.

The check exists to catch an invented figure. A number the merchant wrote is
not one the model invented, so refusing it protects nothing and costs an
answer. What is still refused is exactly what the rule was written for: a
cost per click, a total or a year the model arrived at on its own. A test
holds that line ("the year after" is not 2020 until the model works it out).

## What this costs

A merchant can now have a number of their own repeated back. "Is my cost per
lead 5?" can be answered "no, it is 16.37", but a model that wanted to agree
with a wrong figure the merchant supplied would not be stopped by this check.
The system prompt's instruction to use only looked-up figures is what stands
there, as it did before.

## Found alongside it

- The check read a hyphen between digits as a minus sign, so "2025-11-05"
  became 2025, -11 and -5. It no longer does.
- The transcript recorded every answer as the model's, with nothing refused,
  so a fallback could not be explained afterwards. It now records "template"
  and the numbers refused, and a fallback logs a warning naming the
  conversation.
