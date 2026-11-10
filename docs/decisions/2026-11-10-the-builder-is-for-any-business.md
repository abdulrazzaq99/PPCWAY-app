# The campaign builder is for any business, one question at a time

**10 November 2026.** The client turned down the campaign builder. It was one
long form, and everything in it assumed a tradesman: the only promises it
could check were free quotes, open 24 hours and emergency callouts; its
examples were "water heater repair"; and "get the most leads" assumed every
business wants calls and forms. The owner asked for a stepper that any
business can follow, with a design of its own.

## Any business

The first question is what kind of business it is. There are six kinds:

- we go to our customers;
- customers come to us;
- we advise or do work for clients;
- we sell products online;
- software or an online tool;
- something else.

The kind decides:

- the examples shown;
- which promises are offered first;
- which searches are skipped by default;
- what counts as a win when Google bids: calls and enquiries, visits and
  bookings, enquiries, sales or sign-ups.

The kinds and promises live in `backend/src/ppcway/builder/kinds.py` and
nowhere else. The screen reads them from `/v1/campaigns/start`. The copy
checks refuse any promise's wording unless the merchant ticked it, and Otto
is told which promises it may and may not make. There are fourteen promises.
A phrase belongs to exactly one promise. A longer allowed phrase is blanked
out before shorter ones are checked, so "try it for free" (a free trial) is
not refused as "for free" (a free version).

Drafts from the first builder still check the same way: its three ticks map
to the matching promises, and the emergency tick still licenses "same day".

## One question at a time

The steps are not numbered. They are the brief, written as one sentence that
fills in as the merchant answers:

> Advertise PDFezy, an online tool, selling pdf to word and compress pdf to
> people in Poland and Romania, in English. We can promise a free version and
> no card to start. Spend up to $20.00 a day, for sign-ups.

Each answered part is a link back to its question, the part being asked is
outlined, and the parts still to come wait in grey. By the end the merchant
has read, in plain words, exactly what they are about to approve. That keeps
the rule this product holds to: a sentence before a number. Beside the
questions, a sketch of the ad takes shape from the answers. It says it is a
sketch, because the real wording comes from Otto and real searches.

While the merchant types the landing page, it is read through the audit's
crawler (`/v1/campaigns/site`). The screen then says whose ads they will be,
for example "The ads will be written for PDFezy", before anything is written.

## Not changed

- What happens after "Write my campaign": real searches from Keyword Planner,
  Otto's drafts, the checks, and the review screen before launch.
- Launch: one all-or-nothing request, after Google's own validation.
