# Approved changes reach Google

**5 November 2026.** Step 3 of the owner's list: until today, approving a
change marked it approved and nothing ever sent it. The gateway's `apply_now`
was built and tested, and nothing called it.

## What happens now

- Approving a change sends it in the same request, when writes are on. The
  merchant reads what happened: done, Google's reason for refusing, or that
  writes are off and nothing in their account has changed. Asking for an undo
  works the same way.
- Whatever cannot go at that moment stays approved: held by the write gate or
  a kill switch, by a day's quota, or by a connection that needs renewing.
  `POST /v1/internal/apply` sends it later. It is behind the sync key and meant
  for Cloud Scheduler every 15 minutes. It also sends what the nightly pass
  approves without asking, once auto-apply is on.
- **Writes stay off in production until somebody switches them on.**
  `ADS_WRITES_ENABLED` is not set, and since the same day the gate is also a
  switch in the admin panel (see
  `2026-11-05-writes-are-a-switch-in-the-panel.md`). While it is shut, an
  approval says nothing in the account has changed, and the scheduled pass
  opens no connection to Google.

## What is sent

- **R1** adds the search as an exact-match negative keyword in every ad group
  it was answered from during the 30-day window. The rule adds up the spend
  across all of those ad groups, so excluding the search from one of them
  would make the card's "stops about this much a month" true of only part of
  the money. Exact match is the narrowest exclusion there is.
- **R4** sets the disapproved ad's status to PAUSED.
- **Undo** removes those negative keywords, using the ids Google returned when
  it created them. For an ad, it puts back the status the row recorded before
  the change. It is offered for 30 days after the change was made. The brief
  asked for that limit, but nothing had enforced it.
- What will be sent is written into the log (`payload`) when the change is
  offered. What reaches Google is therefore what the merchant was shown, not
  whatever the rule would find on the day it is sent.

## Decided along the way

- **At most once.** Before the call, one sender takes the change by setting
  `taken_at` in an update that only one sender can win. The request that
  approved the change and the scheduled pass can both reach it, but only one
  sends it. A change that was taken and never answered is reported and never
  sent again. That happens when a send is interrupted between the call and the
  answer, and only someone looking at Google Ads can say whether it landed.
- **Google's answer is kept** (`outcome`): what was created, what was refused
  and why. It can be written once, and a trigger enforces that, as it does for
  `taken_at`. An undo of an exclusion is built from this record, and a failed
  change is explained from it.
- **Freshness is 36 hours, as the brief says**, instead of 3. The code said 36
  in several places and enforced 3. Search terms are settled a day behind and
  read once a night, so every R1 approval made after breakfast was refused.
- **No repeat offers.** A change that is waiting for an answer or has been
  approved is not offered again, at any age. Neither is one made or put back
  in the last 30 days, or one declined by a person or refused by Google in the
  last week. Until now the same search was offered again every night, and
  "Otto will not propose that one again this week" was not true. Expired
  offers and guardrail refusals may still come back.
- **R1 skips searches it cannot exclude**: those over Google's keyword limits
  of 10 words or 80 characters, and those answered from no ad group
  (Performance Max).
- **Putting an exclusion back is not counted as a pause.** It lets a search
  back in. Counted as a pause, it was measured against the account's live ads,
  and on a small account the blast-radius check refused the undo.
- **Google's partial-failure answer is read by position.** Google returns an
  empty result where an operation failed. The old reader assumed failed
  operations were left out of the list, so a refused first operation made the
  second one, which had landed, look as though it had not.

## Known limits

- The scheduled pass needs its Cloud Scheduler job, which is created at
  deploy.
- The nightly Otto pass is scheduled at 4:00, the same minute as a structure
  read. The rules refuse to run while a read is in progress, so a collision
  costs that account its night. Moving the pass to 4:07 is a scheduler change
  for the deploy.
- If a send times out after reaching Google, it is recorded as failed even
  though it may have landed. Retrying an exclusion then produces a refused
  duplicate, not a second exclusion.
- The list of changes is in the Otto inbox only. The home screen's "What Otto
  did" card is still static text, and the new list was not drawn in Figma
  first.
