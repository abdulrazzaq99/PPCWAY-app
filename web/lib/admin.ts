/*
  What the internal panel reads. One file of types so a screen and the server
  reader cannot drift apart.

  Every figure arrives with the sentence the backend wrote for it. The screens
  show that sentence rather than composing their own from the number, because
  two places writing the same sentence is two places to get it wrong -- and the
  backend is the one that knows whether a figure is a count, a state, or
  unknown.
*/

export type Figure = {
  label: string;
  value: number;
  window: string;
  known: boolean;
  change: number | null;
  words: string;
};

export type Stop = {
  scope: string;
  customer_id?: string;
  because: string;
  ours: boolean;
  pulled_at?: string | null;
};

/*
  What Otto proposed, per hour ("today") or per calendar day in UTC, counted by
  the state each change is in now. Optional because an older backend does not
  send it, and the overview must still render against one.
*/
export type Series = {
  step: "hour" | "day";
  points: { start: string; counts: Record<string, number> }[];
};

export type Overview = {
  at: string;
  window: string;
  healthy: boolean;
  trouble: string[];
  writes: { anything_can_be_written: boolean; words: string; stops: Stop[] };
  figures: Record<string, Figure>;
  series?: Series;
};

/* One time a member of staff opened a business. */
export type Look = {
  at: string;
  looked_at: string;
  level: string;
  account_id: string;
  who?: string;
};

/* An account's Google Ads operations today, against Google's daily allowance. */
export type Quota = Room & { day: string };

export type MerchantRow = {
  organization_id: string;
  name: string;
  customer_id: string;
  connected: boolean;
  account_status: string;
  people: number;
  waiting: number;
  applied: number;
  last_sync: string | null;
  trouble: string;
};

export type Flag = {
  name: string;
  on: boolean;
  what_it_does: string;
  changeable: boolean;
  why_not: string;
};

export type PlatformView = {
  words: string;
  anything_can_be_written: boolean;
  may_stop_writes: boolean;
  stops: Stop[];
  flags: Flag[];
};

export type Whoami = {
  staff: boolean;
  level: string;
  may: string[];
  levels: { level: string; what: string }[];
  who?: string;
};

export type Change = {
  id: string;
  kind: string;
  status: string;
  risk: string;
  reason: string;
  created_at: string | null;
};

export type Merchant = {
  organization_id: string;
  name: string;
  created_at: string | null;
  connection: {
    customer_id: string;
    customer_name: string;
    currency: string;
    account_status: string;
  } | null;
  changes: Change[];
};

export type Grant = {
  account_id: string;
  /* The person, by address. Empty from an older backend. */
  who?: string;
  level: string;
  granted: boolean;
  because: string;
  by_account_id: string | null;
  /* Who gave or took it. Empty for the first principal, made by the CLI. */
  by?: string;
  at: string;
};

/* A whole number with thousands grouped, because somebody has to read it. */
export function count(n: number): string {
  return n.toLocaleString("en-CA");
}

/*
  How long ago, in words. "Never" rather than an empty cell: a blank tells a
  reader the screen is broken, and never is a fact about the account.
*/
export function ago(when: string | null): string {
  if (!when) return "Never";
  const then = new Date(when).getTime();
  if (Number.isNaN(then)) return "Never";
  const mins = Math.round((Date.now() - then) / 60000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins} min ago`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours} h ago`;
  return `${Math.round(hours / 24)} d ago`;
}

/*
  Which way a figure moved, as a word rather than an arrow. An arrow has to be
  learnt; "up 14" does not. Null where there is nothing to compare, which is
  not the same as flat.

  The window is named in the words, because "up 14" on its own is not a fact.
*/
export function moved(change: number | null, window = ""): string {
  if (change === null) return "";
  const over = window ? ` vs the ${window} before` : "";
  if (change === 0) return `No change${over}`;
  return change > 0 ? `Up ${count(change)}${over}` : `Down ${count(Math.abs(change))}${over}`;
}

/*
  Every figure has a direction that is good for it. Failures falling is good;
  proposals falling is not. Colour on a change says good or bad, never up or
  down -- a rise in errors set in the same grey as a rise in businesses hides
  the only bad news on the screen.

  Figures with no good direction (how many businesses exist) return "plain":
  colouring them would make the colour mean nothing.
*/
const BETTER_DOWN = new Set([
  "waiting",
  "refused",
  "reverted",
  "model_trouble",
  "syncs_failed",
  "syncs_stuck",
]);
const BETTER_UP = new Set(["merchants", "connected", "applied", "proposed", "people"]);

export function direction(key: string, change: number | null): "plain" | "good" | "bad" {
  // Nothing to compare, or nothing moved, is never a signal. The commonest
  // failure in this kind of screen is a zero change shown as one.
  if (change === null || change === 0) return "plain";
  const rose = change > 0;
  if (BETTER_DOWN.has(key)) return rose ? "bad" : "good";
  if (BETTER_UP.has(key)) return rose ? "good" : "plain";
  return "plain";
}

export type JobRun = {
  id: string;
  customer_id: string;
  kind: string;
  status: string;
  stage: string;
  stuck: boolean;
  took_seconds: number | null;
  started_at: string | null;
  words: string;
};

/*
  One page of job runs, and how many there are in all. `total` and the page
  fields are absent from an older backend, which sends the latest hundred.
*/
export type JobsPage = { runs: JobRun[]; total?: number; offset?: number; limit?: number };

/* The scheduled jobs by the name a person would give them. */
export const JOB_WORDS: Record<string, string> = {
  structure: "Structure sync",
  today: "Today’s figures",
  backfill: "Backfill",
  first: "First sync",
};

export function jobWords(kind: string): string {
  return JOB_WORDS[kind] ?? words(kind);
}

export type Fault = {
  where: string;
  what: string;
  customer_id: string;
  at: string | null;
};

export type Room = {
  customer_id: string;
  used: number;
  allowance: number;
  left: number;
  share_used: number;
  tight: boolean;
  words: string;
};

/* ---------- the console's formatting ---------- */

/*
  Absolute times are UTC everywhere in the console, and say so where they are
  read. The server renders in one zone and a member of staff may sit in
  another; a time that changed with the reader's clock would make two people
  on a call disagree about when something failed.
*/
const UTC = { timeZone: "UTC" } as const;

/* 14:05 */
export function clock(when: string | null): string {
  if (!when) return "";
  const at = new Date(when);
  if (Number.isNaN(at.getTime())) return "";
  return at.toLocaleTimeString("en-GB", { ...UTC, hour: "2-digit", minute: "2-digit" });
}

/* 3 Nov */
export function dayOf(when: string | null): string {
  if (!when) return "";
  const at = new Date(when);
  if (Number.isNaN(at.getTime())) return "";
  return at.toLocaleDateString("en-GB", { ...UTC, day: "numeric", month: "short" });
}

/* 3 Nov 2026 */
export function dateOf(when: string | null): string {
  if (!when) return "";
  const at = new Date(when);
  if (Number.isNaN(at.getTime())) return "";
  return at.toLocaleDateString("en-GB", {
    ...UTC,
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

/* 3 Nov, 14:05 */
export function stamp(when: string | null): string {
  if (!when) return "";
  return `${dayOf(when)}, ${clock(when)}`;
}

/*
  "Today", "Yesterday" or the date, for grouping a feed by day. Compared in UTC
  for the same reason the times are.
*/
export function dayHeading(when: string | null, now = new Date()): string {
  if (!when) return "Undated";
  const at = new Date(when);
  if (Number.isNaN(at.getTime())) return "Undated";
  const day = (d: Date) => Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate());
  const apart = Math.round((day(now) - day(at)) / 86400000);
  if (apart === 0) return "Today";
  if (apart === 1) return "Yesterday";
  return at.toLocaleDateString("en-GB", {
    ...UTC,
    weekday: "long",
    day: "numeric",
    month: "short",
  });
}

/*
  A change with its sign, and a true minus rather than a hyphen, so +4 and −4
  are the same width in the mono and read as a pair.
*/
export function signed(n: number): string {
  if (n === 0) return "0";
  return `${n > 0 ? "+" : "−"}${count(Math.abs(n))}`;
}

/* 2580586343 -> 258-058-6343, the way Google Ads prints a customer id. */
export function adsId(id: string): string {
  const digits = id.replace(/\D/g, "");
  if (digits.length !== 10) return id;
  return `${digits.slice(0, 3)}-${digits.slice(3, 6)}-${digits.slice(6)}`;
}

/* add_negative_keyword -> Add negative keyword */
export function words(code: string): string {
  const plain = code.replace(/[_-]+/g, " ").trim();
  return plain ? plain.charAt(0).toUpperCase() + plain.slice(1) : "";
}

/*
  The five fates the console draws a change in. Eight states collapse to five
  for a chart, and the collapse is written down once, here:

  - open: proposed (the guardrails have not ruled), awaiting approval (a
    merchant has to answer) and approved (said yes, not yet sent);
  - applied: Google has it;
  - refused: a guardrail or a person said no;
  - expired: nobody answered in time, which is not a refusal;
  - undone: put back after it was applied, or sent and refused by Google.
*/
export type Fate = "applied" | "open" | "refused" | "expired" | "undone";

export const FATES: { key: Fate; label: string; states: string[] }[] = [
  { key: "applied", label: "Applied", states: ["applied"] },
  { key: "open", label: "Still open", states: ["proposed", "awaiting_approval", "approved"] },
  { key: "refused", label: "Refused", states: ["rejected"] },
  { key: "expired", label: "Expired", states: ["expired"] },
  { key: "undone", label: "Put back or failed", states: ["reverted", "failed"] },
];

export function fateOf(status: string): Fate {
  return FATES.find((one) => one.states.includes(status))?.key ?? "open";
}

/* How a change's state reads in a row. */
export const STATE_WORDS: Record<string, string> = {
  proposed: "With the guardrails",
  awaiting_approval: "Waiting on the merchant",
  approved: "Approved, not sent",
  applied: "Applied",
  rejected: "Refused",
  expired: "Expired",
  reverted: "Put back",
  failed: "Google refused it",
};

/* Two letters for a business or a person: "Alpha Plumbing" -> AP. */
export function initials(name: string): string {
  const clean = name.replace(/@.*/, "").replace(/[^\p{L}\p{N}\s.]/gu, " ");
  const parts = clean.split(/[\s.]+/).filter(Boolean);
  if (!parts.length) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[1][0]).toUpperCase();
}

/*
  A stable tint for a business or a person, so the same merchant wears the
  same mark on every screen. Six hues 60 degrees apart, none in the violet
  band; identity, not data, so they stay dark and quiet and never reach a
  chart.
*/
const HUES = [12, 40, 150, 188, 214, 336];

export function tintOf(seed: string): { background: string; color: string } {
  let h = 0;
  for (const ch of seed) h = (h * 31 + ch.codePointAt(0)!) >>> 0;
  const hue = HUES[h % HUES.length];
  return { background: `hsl(${hue} 26% 19%)`, color: `hsl(${hue} 62% 80%)` };
}

/*
  Whether a time is old enough to worry about. A sync runs every 15 minutes,
  so an hour is four missed turns and a day is a business working blind.
*/
export function staleness(when: string | null): "fresh" | "late" | "stale" | "never" {
  if (!when) return "never";
  const then = new Date(when).getTime();
  if (Number.isNaN(then)) return "never";
  const hours = (Date.now() - then) / 3600000;
  if (hours < 1) return "fresh";
  if (hours < 24) return "late";
  return "stale";
}

export const LEVEL_WORDS: Record<string, string> = {
  support: "Support",
  engineer: "Engineer",
  principal: "Principal",
};

/*
  The one door to Google, as the console shows it on every screen: whether
  PPCWay may write to any Google Ads account right now, and why not.

  "off" is this deployment's setting, which only a deploy changes. "stopped"
  is a person pulling the platform-wide switch, which a principal can release.
  The backend's sentence says which, and the chip carries it as its title.
*/
export type Door = { state: "on" | "off" | "stopped"; words: string };

export function doorOf(view: PlatformView | null | undefined): Door | undefined {
  if (!view) return undefined;
  if (view.anything_can_be_written) return { state: "on", words: view.words };
  /*
    The deployment's setting outranks any switch, so "stopped" only when the
    setting would allow writing and a person has stopped it anyway. The flag
    is the setting, read from the deployment by the backend.
  */
  const allowed = view.flags.find((one) => one.name === "Writing to Google Ads")?.on ?? false;
  const pulled = view.stops.some((one) => !one.customer_id);
  return { state: allowed && pulled ? "stopped" : "off", words: view.words };
}

/* What the shell shows on every screen: the door, and the count on Failures. */
export type Chrome = { door?: Door; failures?: number };
