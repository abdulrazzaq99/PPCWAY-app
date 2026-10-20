/*
  The audit's history, as the backend sends it. One reading is a number; two are
  an answer, and the answer a small business most wants is whether the thing
  they paid somebody to fix actually got fixed.
*/
export type Point = {
  run_id: string;
  at: string;
  score: number | null;
  needs: number;
  good: number;
  /** "asked" for a run somebody started, "scheduled" for one on the clock. */
  kind: string;
  /** What this reading fixed, and what it broke, against the one before it. */
  fixed: string[];
  broke: string[];
};

export type Moved = { key: string; title: string; summary: string };

export type Changed = {
  first: boolean;
  quiet: boolean;
  at: string;
  before_at: string;
  score: number | null;
  score_before: number | null;
  fixed: Moved[];
  broke: Moved[];
  still: Moved[];
};

export type History = { site: string; points: Point[]; changed: Changed | null };

/** One page the ads send people to, and what is wrong with it. */
export type LandingPage = {
  url: string;
  campaigns: string[];
  read: boolean;
  trouble: string;
  final_url: string;
  title: string;
  headline: string;
  phone_in_view: boolean;
  has_form: boolean;
  /** The buttons above the fold, when there is no form. */
  call_to_action?: string[];
  conversion_tag: boolean;
  tag_fired: boolean;
  overlay: string | null;
  fits_a_phone: boolean;
  jobs: string[];
  ok: boolean;
};
