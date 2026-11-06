/*
  A new campaign, as the builder writes it and the merchant reviews it.
  Written out rather than inferred, so a field renamed on the server breaks
  the build here instead of rendering as "undefined" on the review screen.
*/

export type Place = { resource: string; name: string; kind?: string };

export type Keyword = {
  text: string;
  monthly: number;
  competition: string;
  top_of_page_low: number;
  top_of_page_high: number;
};

export type Theme = {
  name: string;
  keywords: Keyword[];
  headlines: string[];
  descriptions: string[];
  dropped: { text: string; because: string }[];
  /** Why the ad text or keywords came up short, where they did. */
  short: string;
};

export type Plan = {
  name: string;
  daily_budget: number;
  currency: string;
  final_url: string;
  places: Place[];
  language: Place;
  bidding: "clicks" | "leads";
  themes: Theme[];
  negatives: string[];
  ai_written: boolean;
  not_political: boolean;
};

export type Draft = {
  id: string;
  status: "draft" | "launched";
  plan: Plan;
  /** The review screen's summary, built from the plan on the server. */
  sentence: string;
  /** Everything stopping a launch, in words. Empty means it may go. */
  missing: string[];
  outcome: { refused?: string; created?: string[] } | null;
  campaign: string;
  created_at: string | null;
  refused?: { theme: string; text: string; because: string }[];
};

export type Prefill = {
  connected: boolean;
  currency?: string;
  account_name?: string;
  business_name?: string;
  may_launch?: boolean;
};

/** Google's own limits for a responsive search ad. */
export const HEADLINE_CHARS = 30;
export const DESCRIPTION_CHARS = 90;
export const MOST_THEMES = 5;
