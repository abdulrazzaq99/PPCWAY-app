/*
  What an Otto card looks like once it has crossed the wire. Written out
  rather than inferred, because the inbox is the product and a field quietly
  renamed on the server should break the build here rather than render as
  "undefined" to a merchant.
*/
export type Verdict = "real" | "normal" | "thin" | "none";

export type Cite = {
  id: string;
  value: number;
  unit: string;
  as_of: string;
  verdict: Verdict;
};

export type Card = {
  /** The written row's id, or empty for something found but not yet offered. */
  id: string;
  status: string;
  /** False where there is no row yet, so there is nothing to approve. */
  answerable: boolean;
  expires_at?: string | null;
  rule_id: string;
  rule_version: number;
  kind: string;
  title: string;
  about: string;
  target: { kind: string; id: string; label: string };
  reason: string;
  /** Where the words came from. A screen may say so; the brief's AI disclosure needs it. */
  reason_from: string;
  reason_is_ours: boolean;
  impact: {
    money_a_month: number;
    currency: string;
    confidence: number;
    words: string;
    blocking: boolean;
  };
  evidence: Cite[];
  undo: string;
  reversible: boolean;
  risk: "low" | "medium" | "high";
  route: "owner" | "expert";
  priority: number;
  as_of: string | null;
  /** The campaigns it acts in, by Google's id. Absent from older servers. */
  campaigns?: string[];
};

/** A change somebody said yes to, and where it has got to. */
export type Change = {
  id: string;
  status: "approved" | "applied" | "failed" | "reverted" | "rejected";
  rule_id: string;
  title: string;
  target: { kind: string; id: string; label: string };
  /** One sentence on where it stands, written by the server. */
  words: string;
  /** True while it was made in the last thirty days and nothing is putting it back. */
  may_undo: boolean;
  undo: string;
  approved_at: string | null;
  applied_at: string | null;
  reverted_at: string | null;
  campaigns?: string[];
};

export type Inbox = {
  connected: boolean;
  cards: Card[];
  /** What became of the changes already said yes to. Absent from older servers. */
  changes?: Change[];
  held_back: number;
  used_this_week: number;
  room_left: number;
  nothing_because: string;
  /** Which rules ran, and which the client has not specified yet. */
  ran: string[];
  not_specified: string[];
  ran_at: string;
  target_cost_per_lead?: number;
  /** Why the checks that rest on leads did not run: the account counts no enquiries. */
  cannot_check?: string;
  /** Found but not offered yet, in words: a campaign waiting for a budget ceiling. */
  notes?: { campaign: string; words: string }[];
};

export type Said = { kind: string; words: string };

export function money(amount: number, currency: string): string {
  const whole = amount.toLocaleString("en-GB", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  // The code beside the number rather than a bare symbol: a symbol is the
  // fastest way to show a Canadian merchant euros.
  return currency ? `${whole} ${currency}` : whole;
}

export function when(stamp: string | null): string {
  if (!stamp) return "";
  const read = new Date(stamp);
  if (Number.isNaN(read.getTime())) return "";
  return read.toLocaleDateString("en-GB", { day: "numeric", month: "long" });
}
