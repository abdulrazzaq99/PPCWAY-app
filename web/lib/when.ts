/*
  How long ago, and how new, in the words a person would use.

  Both of these are on screens that read our own mirror rather than Google, and
  a number from a database has to say how old it is. "Last read four minutes
  ago" is the difference between a dashboard and a guess.
*/

/** How long ago something happened: "just now", "4 minutes ago", "yesterday". */
export function ago(when: string): string {
  const minutes = Math.max(0, Math.round((Date.now() - new Date(when).getTime()) / 60000));
  if (minutes < 1) return "just now";
  if (minutes === 1) return "a minute ago";
  if (minutes < 60) return `${minutes} minutes ago`;
  const hours = Math.round(minutes / 60);
  if (hours === 1) return "an hour ago";
  if (hours < 24) return `${hours} hours ago`;
  const days = Math.round(hours / 24);
  return days === 1 ? "yesterday" : `${days} days ago`;
}

/*
  Google's bidding needs about a week of a campaign's own data before its
  numbers mean anything. Judging a campaign inside that week is the commonest
  mistake a small advertiser makes, so the screen says so instead of letting
  somebody draw a conclusion from three days.
*/
export const LEARNING_DAYS = 7;

/** Which day of its first week a campaign is on, or null once it is past it. */
export function learning(startsAt: string | undefined, now = new Date()): number | null {
  if (!startsAt) return null;
  // Google writes "2026-10-18 00:00:00" in the account's own time zone. Read
  // the day and ignore the clock: a campaign is a day old, not 19 hours old.
  const day = startsAt.slice(0, 10);
  const started = new Date(`${day}T00:00:00`);
  if (Number.isNaN(started.getTime())) return null;
  const since = Math.floor((now.getTime() - started.getTime()) / 86_400_000) + 1;
  if (since < 1 || since > LEARNING_DAYS) return null;
  return since;
}
