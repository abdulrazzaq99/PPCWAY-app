/*
  The free audit, as the page sees it.

  One rule runs through all of this: the findings are the server's to give out,
  not the page's to hide. Everything before the code is checked comes back
  without them, so a reader of this file — or of the network tab — learns
  nothing a stranger should not know.
*/
export type Runner = "me" | "agency" | "none" | "self_agency";
export type Goal = "sales" | "leads" | "calls" | "signups";
export type SpendBand = "none" | "under_1k" | "1k_5k" | "5k_25k" | "25k_plus";

export const RUNNERS: { id: Runner; label: string }[] = [
  { id: "me", label: "I run them" },
  { id: "agency", label: "An agency runs them" },
  { id: "none", label: "Not running ads yet" },
  { id: "self_agency", label: "I'm an agency" },
];

export const GOALS: { id: Goal; title: string; detail: string }[] = [
  { id: "sales", title: "Online sales", detail: "Online stores and ecommerce" },
  { id: "leads", title: "Leads and demos", detail: "Software, B2B and services" },
  { id: "calls", title: "Calls and bookings", detail: "Local and service businesses" },
  { id: "signups", title: "Sign-ups and installs", detail: "Apps and subscriptions" },
];

export const SPENDS: { id: SpendBand; label: string }[] = [
  { id: "none", label: "Not yet" },
  { id: "under_1k", label: "Under $1k" },
  { id: "1k_5k", label: "$1k–$5k" },
  { id: "5k_25k", label: "$5k–$25k" },
  { id: "25k_plus", label: "$25k+" },
];

export type Choice = { kind: string; label: string; about: string };

/*
  What sort of business this looks like. `sure` is the part that matters: an
  unsure guess is shown as a question, a sure one as a statement, and either
  can be overruled.
*/
export type Who = {
  found: boolean;
  matched: boolean;
  listing_name: string;
  place_id: string;
  kind: string;
  label: string;
  about: string;
  sure: boolean;
  because: string;
  choices: Choice[];
};

export type Stage = { label: string; state: "done" | "running" | "todo" };

export type Summary = {
  score: number;
  band: "good" | "warn";
  verdict: string;
  business: string;
  goal: string;
  spend: string;
  to_fix: number;
  to_improve: number;
  working: number;
};

export type Finding = {
  id: string;
  severity: "fix" | "improve" | "good";
  title: string;
  detail: string;
  fix: string;
};

export type Waste = { low: number; high: number | null; said: string } | null;

export type Progress = {
  audit_id: string;
  status: "queued" | "running" | "done" | "failed";
  stages: Stage[];
  percent: number;
  pages_read: number;
  error?: string;
  summary?: Summary;
  verified?: boolean;
};

export type Unlocked = Summary & {
  verified: true;
  findings: Finding[];
  waste: Waste;
  open_again: string;
};

/** What the visit came in on, kept with the lead rather than in the address bar. */
export function cameFrom(): Record<string, string> {
  if (typeof window === "undefined") return {};
  const found: Record<string, string> = {};
  const here = new URLSearchParams(window.location.search);
  for (const key of [
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "gclid",
    "gbraid",
    "wbraid",
  ]) {
    const value = here.get(key);
    if (value) found[key] = value.slice(0, 200);
  }
  return found;
}

/*
  One event per session, as the spec asks. `lead_verified` is the one that
  matters: it is the conversion a real person at a real address completed, and
  the only one worth bidding on.
*/
const fired = new Set<string>();

export function track(event: string, params: Record<string, unknown> = {}): void {
  if (typeof window === "undefined" || fired.has(event)) return;
  fired.add(event);
  const w = window as unknown as { dataLayer?: unknown[] };
  if (Array.isArray(w.dataLayer)) w.dataLayer.push({ event, ...params });
}

type Said = { error?: string; detail?: string };

async function ask<T>(path: string, options: { method?: string; body?: unknown } = {}): Promise<T> {
  const res = await fetch(path, {
    method: options.method ?? "GET",
    headers: options.body ? { "content-type": "application/json" } : undefined,
    body: options.body ? JSON.stringify(options.body) : undefined,
    cache: "no-store",
  });
  const said = (await res.json().catch(() => ({}))) as Said & T;
  if (!res.ok) throw new Error(said.error ?? said.detail ?? "That did not work.");
  return said;
}

export const funnel = {
  identify: (body: { business_name: string; site: string; place_id?: string }) =>
    ask<Who>("/api/public/identify", { method: "POST", body }),

  start: (body: {
    business_name: string;
    site: string;
    runner: Runner;
    goal: Goal;
    spend_band: SpendBand;
    kind: string;
    kind_is_theirs: boolean;
    place_id: string;
    came_from: Record<string, string>;
  }) => ask<{ audit_id: string }>("/api/public/audits", { method: "POST", body }),

  progress: (id: string) => ask<Progress>(`/api/public/audits/${encodeURIComponent(id)}`),

  lead: (
    id: string,
    body: {
      name: string;
      email: string;
      phone: string;
      tips_opt_in: boolean;
      came_from: Record<string, string>;
    },
  ) =>
    ask<{ sent: boolean; email: string }>(`/api/public/audits/${encodeURIComponent(id)}/lead`, {
      method: "POST",
      body,
    }),

  resend: (id: string) =>
    ask<{ sent: boolean; wait_seconds?: number }>(
      `/api/public/audits/${encodeURIComponent(id)}/resend`,
      { method: "POST", body: {} },
    ),

  verify: (id: string, code: string) =>
    ask<Unlocked>(`/api/public/audits/${encodeURIComponent(id)}/verify`, {
      method: "POST",
      body: { code },
    }),

  open: (token: string) => ask<Unlocked>(`/api/public/audits/open/${encodeURIComponent(token)}`),
};
