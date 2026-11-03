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

export type Overview = {
  at: string;
  window: string;
  healthy: boolean;
  trouble: string[];
  writes: { anything_can_be_written: boolean; words: string; stops: Stop[] };
  figures: Record<string, Figure>;
};

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
  level: string;
  granted: boolean;
  because: string;
  by_account_id: string | null;
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
*/
export function moved(change: number | null): string {
  if (change === null) return "";
  if (change === 0) return "No change";
  return change > 0 ? `Up ${count(change)}` : `Down ${count(Math.abs(change))}`;
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
