#!/usr/bin/env bash
# Rotate the sync key that guards the API's /v1/internal endpoints, and point
# every scheduled job at the new one. Also makes sure the send pass exists and
# the nightly Otto pass runs at 4:07, clear of the reads that start on the hour.
#
# Written on 6 November 2026, after a failed `gcloud scheduler jobs create`
# printed the old key in its error message. Run it whenever the key may have
# been seen:
#
#     bash backend/scripts/rotate_sync_key.sh
#
# Nothing here prints the new key. Every command that could echo it has its
# output discarded, and any error is shown with the key masked: gcloud repeats
# an argument it does not recognise in full. Safe to run again if it stops part
# way; each step repeats harmlessly or updates what the last run made.
set -uo pipefail

G=${GCLOUD:-$HOME/google-cloud-sdk/bin/gcloud}
P=ppcway-509313
L=northamerica-northeast2
API=https://ppcway-api-734687676224.northamerica-northeast2.run.app
JOBS="ppcway-sync-structure ppcway-sync-today ppcway-sync-backfill ppcway-otto-nightly ppcway-audit-nightly ppcway-alerts ppcway-post-weekly"

KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')

stop() {
  echo "STOPPED: $1"
  unset KEY
  exit 1
}

# Run a command with its output thrown away; on failure, show the error with
# the key masked.
quietly() {
  local err
  if ! err=$("$@" 2>&1 >/dev/null); then
    stop "${err//$KEY/<new key>}"
  fi
}

# 1. The new key, as the next version of the secret the API reads.
if ! err=$(printf %s "$KEY" | $G secrets versions add sync-key --data-file=- --project=$P 2>&1 >/dev/null); then
  stop "storing the key: $err"
fi
V=$($G secrets versions list sync-key --project=$P --sort-by=~createTime --limit=1 --format='value(name.basename())')
echo "1/5 new key stored as version $V of sync-key"

# 2. A new API revision that reads exactly that version, with all traffic on
#    it. Pinned rather than "latest", so the new revision is certain to read
#    the new key and the old key stops working the moment it takes traffic.
quietly $G run services update ppcway-api --region=$L --project=$P --update-secrets="SYNC_KEY=sync-key:$V" --quiet
quietly $G run services update-traffic ppcway-api --to-latest --region=$L --project=$P --quiet
echo "2/5 API serving $($G run services describe ppcway-api --region=$L --project=$P --format='value(status.traffic[0].revisionName)') with the new key"

# 3. Every scheduled job sends the new key.
for job in $JOBS; do
  quietly $G scheduler jobs update http "$job" --location=$L --project=$P --update-headers="x-sync-key=$KEY" --quiet
done
echo "3/5 the seven scheduled jobs send the new key"

# 4. The nightly pass at 4:07: at 4:00 it starts in the same second as the
#    quarter-hourly and hourly reads, and the rules refuse to run on an
#    account that is half read.
quietly $G scheduler jobs update http ppcway-otto-nightly --location=$L --project=$P --schedule="7 4 * * *" --quiet
echo "4/5 nightly pass runs at 4:07"

# 5. The send pass, every 15 minutes at :05, :20, :35 and :50. `create` takes
#    --headers; only `update` takes --update-headers.
if $G scheduler jobs describe ppcway-otto-apply --location=$L --project=$P >/dev/null 2>&1; then
  quietly $G scheduler jobs update http ppcway-otto-apply --location=$L --project=$P --update-headers="x-sync-key=$KEY" --quiet
else
  quietly $G scheduler jobs create http ppcway-otto-apply --location=$L --project=$P \
    --schedule="5-59/15 * * * *" --time-zone="America/Toronto" \
    --uri="$API/v1/internal/apply" --http-method=POST \
    --headers="x-sync-key=$KEY" --attempt-deadline=600s --quiet
fi
echo "5/5 send pass scheduled"

# Proof the API and the jobs now agree: one read-only internal call with the
# new key. Its answer is thrown away; only the status is shown.
code=$(curl -s -o /dev/null -w '%{http_code}' -H "x-sync-key: $KEY" "$API/v1/internal/gate")
unset KEY
echo "check: an internal call with the new key answered $code (200 is right)"
$G scheduler jobs list --location=$L --project=$P --format="table(name.basename(),schedule,state)"
