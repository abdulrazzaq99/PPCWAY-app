/*
  What the mirror answers with.

  One shape for home, campaigns and reports, so a field added to the API is
  added in one place rather than three. Everything is optional: the same
  endpoint answers "we have not read this account yet" with a sentence, and a
  screen that assumes a number is there is a screen that breaks on day one.
*/
export type AdsDay = {
  date: string;
  calls: number;
  forms: number;
  leads: number;
  cost: number;
  clicks: number;
  impressions: number;
};

export type AdsRow = {
  campaign_id: string;
  name: string;
  status: string;
  serving?: string;
  budget: number;
  leads: number;
  cost: number;
  clicks?: number;
  impressions?: number;
  cost_per_lead: number;
  /** Google's own "yyyy-MM-dd HH:mm:ss", which the Learning chip counts from. */
  starts_at?: string;
  /** Gone from Google, kept here, because it spent real money while it ran. */
  gone?: boolean;
  days?: AdsDay[];
};

/** One thing on the "needs you" list. The words are written by the backend. */
export type AdsNeed = {
  kind: "spend_no_leads" | "ad_refused" | "changed_in_google" | string;
  label: string;
  what: string;
  campaign_id?: string;
};

/** Something somebody changed in Google Ads, not here. */
export type AdsChange = {
  kind: string;
  label: string;
  summary: string;
  when: string | null;
};

export type AdsSummary = {
  read: boolean;
  trouble?: string;
  /** Google has ended the permission; the only way forward is to grant it again. */
  reconnect?: boolean;
  /** Connected, but they have not said which of their accounts to read. */
  choose?: boolean;
  currency?: string;
  days?: number;
  /** The window the figures cover, as the backend worked it out. */
  starts_on?: string;
  ends_on?: string;
  leads?: number;
  calls?: number;
  forms?: number;
  cost?: number;
  clicks?: number;
  impressions?: number;
  cost_per_lead?: number;
  leads_before?: number;
  cost_before?: number;
  cost_per_lead_before?: number;
  month_cost?: number;
  month_day?: number;
  month_days?: number;
  monthly_budget?: number;
  series?: AdsDay[];
  campaigns?: AdsRow[];
  needs?: AdsNeed[];
  activity?: AdsChange[];
  /** When the last finished sync finished. A figure from our database says its age. */
  looked_at?: string | null;
  held_days?: number;
  /** "mirror" for our own database, "live" for the minutes before the first sync. */
  source?: "mirror" | "live";
};
