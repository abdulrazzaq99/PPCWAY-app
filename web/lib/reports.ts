import type { AdsDay, AdsRow } from "@/lib/ads";

/*
  The report's shape, as the backend sends it. The verdict words and the
  definitions are written there rather than here on purpose: the app, a shared
  link and a printed copy all read the same sentences, so they cannot drift.
*/
export type Figure = {
  key: string;
  label: string;
  kind: "count" | "money" | "rate" | string;
  value: number;
  before: number | null;
  year_ago: number | null;
  change: number | null;
  /** "real", "normal", "thin", or "none" where no test applies. */
  verdict: "real" | "normal" | "thin" | "none" | string;
  words: string;
  /** Which test was used, named so the number can be argued with. */
  test: string;
};

export type Definition = { term: string; what: string };

export type Share = { id: string; expires_at: string; opened: number; sent_to: string };

export type ReportSaid = {
  read: boolean;
  trouble?: string;
  choose?: boolean;
  currency?: string;
  days?: number;
  held_days?: number;
  starts_on?: string;
  ends_on?: string;
  figures?: Figure[];
  campaigns?: AdsRow[];
  series?: AdsDay[];
  year_held?: boolean;
  sentence?: string;
  definitions?: Definition[];
  looked_at?: string | null;
  business?: string;
  /** Set on a report read through a shared link rather than in the app. */
  shared?: boolean;
  expires_at?: string;
  shares?: Share[];
};
