/*
  The Conversions screens' data, field for field as the API sends it
  (backend `api/app.py` under `/v1/conversions`, built by `ads/conversions.py`),
  so a rename on the server breaks the build here instead of rendering
  "undefined". Every name is the server's.
*/

export type Snippet = {
  /** WEBPAGE, WEBPAGE_ONCLICK, CLICK_TO_CALL or WEBSITE_CALL. */
  type: string;
  /** HTML or AMP. */
  page_format: string;
  global_site_tag: string;
  event_snippet: string;
};

export type Action = {
  resource: string;
  id: string;
  name: string;
  status: string;
  state: string;
  type: string;
  source: string;
  source_label: string;
  origin: string;
  category: string;
  category_label: string;
  primary: boolean;
  counting: string;
  value: { default: number | null; currency: string; always: boolean };
  click_days: number | null;
  view_days: number | null;
  attribution: string;
  call_seconds: number | null;
  app_id: string;
  imported: boolean;
  editable: boolean;
  recent: number;
  snippets: Snippet[];
};

export type SourceKey =
  | "website"
  | "calls_from_ads"
  | "calls_from_website"
  | "call_uploads"
  | "offline"
  | "app_download"
  | "app_purchase";

export type SourceOption = {
  label: string;
  categories: { id: string; label: string }[];
  call: boolean;
  app: boolean;
};

export type Tag = {
  read: boolean;
  google_tag: boolean;
  this_account: boolean;
  tag_manager: boolean;
  found_ids: string[];
};

export type Summary = {
  connected: boolean;
  currency?: string;
  account_name?: string;
  website?: string;
  may_change?: boolean;
  tag?: Tag;
  /** The ways to measure that setup offers. */
  source_options?: Partial<Record<SourceKey, SourceOption>>;
  /** Which of Google's four data sources the account already measures. */
  sources?: { website: boolean; app: boolean; calls: boolean; offline: boolean };
  read?: boolean;
  reason?: string;
  tracking_id?: string;
  tracking_status?: string;
  data_terms?: boolean;
  actions?: Action[];
  importable?: Action[];
  global_site_tag?: string;
};

export type Refusal = { name?: string; message: string; code: string };

export type Created = {
  created: Action[];
  created_names: string[];
  refused: Refusal[];
  tracking_id: string;
  global_site_tag: string;
};

export type Changed = { changed: string[]; refused: Refusal[] };

/** One action as "Create conversion actions" posts it. */
export type NewAction = {
  source: SourceKey;
  name: string;
  category: string;
  value: ValueMode;
  amount: number;
  count: "every" | "one";
  click_days: number;
  view_days: number;
  attribution: "data_driven" | "last_click";
  primary: boolean;
  call_seconds: number;
  app_id: string;
};

export type ValueMode = "same" | "different" | "none";

/** The settings Google's screen asks for, while the merchant is still typing. */
export type Settings = {
  value: ValueMode;
  amount: number | null;
  count: "every" | "one";
  click_days: number | null;
  view_days: number | null;
  /** Empty when Google's reply names a model PPCWay does not offer (an old rules-based one). */
  attribution: "data_driven" | "last_click" | "";
  primary: boolean;
  call_seconds: number | null;
};

/** Which settings apply, by the kind of action. */
export type Kind = {
  /** A call: a click window of 1 to 60 days, no view-through window, a call length. */
  call: boolean;
  /** Google's screen offers a view-through window. */
  view: boolean;
  /** "Use different values for each conversion" is on offer (not for calls). */
  different: boolean;
};

/** Google's category order, as its Conversions summary lists goals. */
export const CATEGORY_ORDER = [
  "PURCHASE",
  "ADD_TO_CART",
  "BEGIN_CHECKOUT",
  "SUBSCRIBE_PAID",
  "SUBMIT_LEAD_FORM",
  "BOOK_APPOINTMENT",
  "SIGNUP",
  "REQUEST_QUOTE",
  "GET_DIRECTIONS",
  "OUTBOUND_CLICK",
  "CONTACT",
  "PHONE_CALL_LEAD",
  "PAGE_VIEW",
  "ENGAGEMENT",
  "DOWNLOAD",
  "IMPORTED_LEAD",
  "QUALIFIED_LEAD",
  "CONVERTED_LEAD",
  "STORE_VISIT",
  "STORE_SALE",
  "DEFAULT",
];

/** The setup source each kind of action was created from, for its category list. */
export const SOURCE_OF_TYPE: Record<string, SourceKey> = {
  WEBPAGE: "website",
  WEBPAGE_CODELESS: "website",
  AD_CALL: "calls_from_ads",
  WEBSITE_CALL: "calls_from_website",
  UPLOAD_CALLS: "call_uploads",
  UPLOAD_CLICKS: "offline",
  GOOGLE_PLAY_DOWNLOAD: "app_download",
  GOOGLE_PLAY_IN_APP_PURCHASE: "app_purchase",
};

export const DATA_DRIVEN = "GOOGLE_SEARCH_ATTRIBUTION_DATA_DRIVEN";
export const LAST_CLICK = "GOOGLE_ADS_LAST_CLICK";

/** Which settings an existing action has, by its type. */
export function kindOfType(type: string): Kind {
  const call = type === "AD_CALL" || type === "WEBSITE_CALL";
  // Clicks on a number in a mobile site: no call length and no view-through on Google's page.
  const quiet = type === "UPLOAD_CALLS" || type === "UPLOAD_CLICKS" || type === "CLICK_TO_CALL";
  return { call, view: !call && !quiet, different: !call && type !== "CLICK_TO_CALL" };
}

/** Which settings a new action has, by the source it is set up from. */
export function kindOfSource(source: SourceKey, option?: SourceOption): Kind {
  const call = Boolean(option?.call);
  // Google's own screens offer no view-through window on imports and uploads.
  const upload = source === "offline" || source === "call_uploads";
  return { call, view: !call && !upload, different: !call };
}

/** The Conversions API, through `app/api/conversions`. Never throws. */
export async function talk<T>(path: string, body?: unknown): Promise<{ ok: boolean; data: T }> {
  try {
    const res = await fetch(path ? `/api/conversions/${path}` : "/api/conversions", {
      method: body === undefined ? "GET" : "POST",
      headers: body === undefined ? undefined : { "content-type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    const data = (await res.json().catch(() => ({}))) as T;
    return { ok: res.ok, data };
  } catch {
    return { ok: false, data: { error: "PPCWay is not reachable right now." } as T };
  }
}

/** The error a failed call said, in words. */
export function said(data: unknown, fallback = "That did not work."): string {
  const error = (data as { error?: unknown } | null)?.error;
  return typeof error === "string" ? error : fallback;
}

/** "pdfezy.com" from "https://www.pdfezy.com/pricing". */
export function domainOf(site: string): string {
  try {
    return new URL(site).hostname.replace(/^www\./, "");
  } catch {
    return site;
  }
}

/** An address someone typed, made into one the API takes. Empty when it is not one. */
export function asAddress(typed: string): string {
  const raw = typed.trim();
  if (!raw) return "";
  const full = /^https?:\/\//i.test(raw) ? raw : `https://${raw}`;
  try {
    const url = new URL(full);
    return url.hostname.includes(".") ? url.toString() : "";
  } catch {
    return "";
  }
}

/** A count of conversions, as Google's table writes them. */
export function conversions(n: number): string {
  return n.toLocaleString(undefined, { maximumFractionDigits: 2 });
}
