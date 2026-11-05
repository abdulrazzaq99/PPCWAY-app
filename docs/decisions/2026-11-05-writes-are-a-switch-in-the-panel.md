# Writes to Google Ads are a switch in the admin panel

**5 November 2026.** At the owner's request: "redeploy after every single time
is not good approach."

## The decision

The write gate is a switch on the internal panel's Settings screen, as well as
the deployment's `ADS_WRITES_ENABLED`. The most recent time somebody used the
switch decides whether writes are on, in either direction. Until anybody has
used it, the deployment's setting decides.

This reverses what the panel was built to do. `staff/controls.py` said a
button that could turn on live writing would be "the most dangerous control in
the product, so it does not exist." It exists now, built like the kill switch
rather than like a preference:

- **Principal access only.** That is the level that already holds the kill
  switch and grants access to other people.
- **Switching on needs a reason** of at least 12 characters. It is kept with
  the person's name, because switching on is the direction that changes what
  happens to a merchant's money. Switching off needs nothing, because nobody
  should hesitate to stop.
- **Every switch is a row in `ads_write_gate`**: on or off, who, when and why.
  The database refuses to update or delete a row, so "who turned writes on
  last Tuesday, and why?" survives anybody tidying up.
- **A stop still wins.** "Stop writes everywhere" and the per-account stops
  outrank the switch, so stopping everything stays a single button whatever
  the switch says.
- **It is read when each change is sent**, never cached. Switching writes off
  in the middle of a send pass stops the rest of that pass.

## What stays a deploy

Applying changes without asking (`OTTO_AUTO_APPLY`) is still the deployment's
setting. It is the client's decision, tied to the Terms and the consent
wording, and is not something to flip while testing. The other settings on the
screen are unchanged.

## What this costs

Anybody with principal access can now start live writes without a deploy and
without review. The guardrails, the at-most-once send and the 30-day undo all
still apply, but the last check on writes being switched on is a person typing
a reason, not a pull request.
