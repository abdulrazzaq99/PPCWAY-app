/*
  A new campaign on Google's own steps (backend `builder/spec.py`), written out
  field for field so a rename on the server breaks the build here instead of
  rendering "undefined". Every name is the server's.
*/

export type Place = { resource: string; name: string; kind?: string };
export type Radius = {
  label: string;
  latitude: number;
  longitude: number;
  radius: number;
  units: "KILOMETERS" | "MILES";
};
export type GoalPair = { category: string; origin: string; name?: string };
export type Match = "BROAD" | "PHRASE" | "EXACT";
export type Pin = "HEADLINE_1" | "HEADLINE_2" | "HEADLINE_3" | "DESCRIPTION_1" | "DESCRIPTION_2";
export type Day =
  "MONDAY" | "TUESDAY" | "WEDNESDAY" | "THURSDAY" | "FRIDAY" | "SATURDAY" | "SUNDAY";
export type CampaignType =
  "SEARCH" | "PERFORMANCE_MAX" | "DEMAND_GEN" | "DISPLAY" | "SHOPPING" | "APP";
export type Objective = "sales" | "leads" | "traffic" | "awareness" | "app" | "local" | "none";

export type Segment = {
  kind: "user_list" | "user_interest" | "custom_audience" | "combined_audience";
  resource: string;
  name: string;
  excluded?: boolean;
  /** Only on search results: which of Google's groups it is in. */
  group?: string;
  size?: number | null;
};
export type Brand = { id: string; name: string };
export type Keyword = {
  text: string;
  match: Match;
  monthly?: number;
  competition?: string;
  top_of_page_low?: number;
  top_of_page_high?: number;
};
export type AdText = { text: string; pin: Pin | null };
export type SearchAd = {
  final_url: string;
  path1: string;
  path2: string;
  headlines: AdText[];
  descriptions: AdText[];
  ai_written: boolean;
};
export type AdGroup = {
  name: string;
  keywords: Keyword[];
  negatives: Keyword[];
  ads: SearchAd[];
  default_bid: number | null;
  locations_of_interest: Place[];
  dropped: { text: string; because: string }[];
  short: string;
};
export type Sitelink = {
  text: string;
  description1: string;
  description2: string;
  final_url: string;
};
export type Snippet = { header: string; values: string[] };
export type PriceItem = {
  header: string;
  description: string;
  price: number;
  unit: "" | "PER_HOUR" | "PER_DAY" | "PER_WEEK" | "PER_MONTH" | "PER_YEAR" | "PER_NIGHT";
  final_url: string;
};
export type Price = {
  type: string;
  qualifier: "" | "FROM" | "UP_TO" | "AVERAGE";
  language: string;
  items: PriceItem[];
};
export type Promotion = {
  item: string;
  occasion: string;
  discount: "percent" | "money";
  amount: number;
  up_to: boolean;
  details: "none" | "code" | "orders_over";
  code: string;
  orders_over: number;
  final_url: string;
  start: string | null;
  end: string | null;
  language: string;
};
export type LeadForm = {
  business_name: string;
  headline: string;
  description: string;
  privacy_policy_url: string;
  call_to_action: string;
  call_to_action_description: string;
  fields: string[];
  post_submit_headline: string;
  post_submit_description: string;
};
export type AppLink = {
  app_id: string;
  store: "GOOGLE_APP_STORE" | "APPLE_APP_STORE";
  link_text: string;
};
/** An image already in the account's asset library. */
export type AdImage = { asset: string; url: string; width: number; height: number; name: string };

/** One Demand Gen ad: Google's "Image ad", "Video ad" or "Carousel ad". */
export type DemandGenAd = {
  format: "image" | "video" | "carousel";
  name: string;
  final_url: string;
  headlines: string[];
  long_headlines: string[];
  descriptions: string[];
  business_name: string;
  call_to_action: string;
  marketing_images: AdImage[];
  square_images: AdImage[];
  portrait_images: AdImage[];
  logos: AdImage[];
  videos: string[];
  /** Each card: an image, a headline, the button's words and its own final URL. */
  cards: { image: AdImage | null; headline: string; call_to_action: string; final_url: string }[];
};

export type Spec = {
  v: 2;
  objective: Objective;
  type: CampaignType;
  goals: { account_default: boolean; chosen: GoalPair[]; available: GoalPair[] };
  ways: {
    website: boolean;
    website_url: string;
    calls: boolean;
    phone_country: string;
    phone_number: string;
    store_visits: boolean;
    app: boolean;
    app_id: string;
    app_store: "GOOGLE_APP_STORE" | "APPLE_APP_STORE";
    lead_forms: boolean;
  };
  name: string;
  eu_political: boolean | null;
  currency: string;
  time_zone: string;
  bidding: {
    focus: "conversions" | "conversion_value" | "clicks" | "impression_share";
    strategy: "" | "manual_cpc";
    set_target: boolean;
    target_cpa: number | null;
    target_roas: number | null;
    max_cpc: number | null;
    impression_location: "ANYWHERE_ON_PAGE" | "TOP_OF_PAGE" | "ABSOLUTE_TOP_OF_PAGE";
    impression_percent: number | null;
    impression_max_cpc: number | null;
    explore: boolean;
    explore_tolerance: number;
    new_customers: "off" | "bid_higher" | "only";
    new_customer_value: number | null;
    default_bid: number | null;
    enhanced: boolean;
  };
  networks: { search_partners: boolean; display: boolean };
  locations: {
    mode: "all" | "home" | "custom";
    home: Place | null;
    targets: Place[];
    excluded: Place[];
    radius: Radius[];
    target_option: "PRESENCE_OR_INTEREST" | "PRESENCE";
    exclude_option: "PRESENCE";
  };
  languages: Place[];
  audiences: { mode: "observation" | "targeting"; segments: Segment[] };
  ai_max: {
    enabled: boolean;
    search_term_matching: boolean;
    text_customization: boolean;
    final_url_expansion: boolean;
    url_exclusions: string[];
    brand_inclusions: Brand[];
    brand_exclusions: Brand[];
    text_guidelines: { term_exclusions: string[]; messaging_restrictions: string[] };
  };
  dates: { start: string | null; end: string | null };
  schedule: {
    day: Day;
    start_hour: number;
    start_minute: 0 | 15 | 30 | 45;
    end_hour: number;
    end_minute: 0 | 15 | 30 | 45;
    bid_adjustment: number | null;
  }[];
  /** Bid adjustment per device in percent; -100 stops ads on it. */
  devices: Partial<Record<"DESKTOP" | "MOBILE" | "TABLET" | "CONNECTED_TV", number>>;
  url_options: {
    tracking_template: string;
    final_url_suffix: string;
    custom_parameters: { key: string; value: string }[];
  };
  ip_exclusions: string[];
  ad_rotation: "OPTIMIZE" | "ROTATE_FOREVER";
  negatives: Keyword[];
  negative_lists: { resource: string; name: string }[];
  generation: {
    url: string;
    summary: string;
    services: string[];
    kind: string;
    promises: string[];
    done: boolean;
  };
  ad_groups: AdGroup[];
  assets: {
    sitelinks: Sitelink[];
    callouts: string[];
    snippets: Snippet[];
    call: boolean;
    call_country: string;
    call_number: string;
    business_name: string;
    logo: AdImage | null;
    images: AdImage[];
    price: Price | null;
    promotion: Promotion | null;
    lead_form: LeadForm | null;
    app: AppLink | null;
  };
  budget: { type: "daily" | "total"; amount: number; shared: string; shared_name: string };
  pmax: {
    asset_group: {
      name: string;
      final_url: string;
      path1: string;
      path2: string;
      headlines: string[];
      long_headlines: string[];
      descriptions: string[];
      business_name: string;
      call_to_action: string;
      marketing_images: AdImage[];
      square_images: AdImage[];
      portrait_images: AdImage[];
      logos: AdImage[];
      landscape_logos: AdImage[];
      videos: string[];
      search_themes: string[];
      signal: Segment[];
      sitelinks: Sitelink[];
    };
    brand_guidelines: { enabled: boolean; main_color: string; accent_color: string; font: string };
    text_customization: boolean;
    final_url_expansion: boolean;
    url_exclusions: string[];
    brand_exclusions: Brand[];
    excluded_ages: string[];
    excluded_genders: string[];
    text_guidelines: { term_exclusions: string[]; messaging_restrictions: string[] };
  };
  demand_gen: {
    campaign_level_targeting: boolean;
    ad_group_name: string;
    channels: "all" | "choose";
    selected: string[];
    optimized_targeting: boolean;
    segments: Segment[];
    ads: DemandGenAd[];
    target_cpc: number | null;
  };
  display: {
    ad_group_name: string;
    optimized_targeting: boolean;
    segments: Segment[];
    keywords: string[];
    default_bid: number | null;
    final_url: string;
    headlines: string[];
    long_headline: string;
    descriptions: string[];
    business_name: string;
    call_to_action: string;
    marketing_images: AdImage[];
    square_images: AdImage[];
    logos: AdImage[];
    landscape_logos: AdImage[];
    videos: string[];
  };
  shopping: {
    merchant_id: number | null;
    feed_label: string;
    priority: 0 | 1 | 2;
    enable_local: boolean;
    ad_group_name: string;
    default_bid: number | null;
  };
  app: {
    subtype: "APP_CAMPAIGN" | "APP_CAMPAIGN_FOR_ENGAGEMENT" | "APP_CAMPAIGN_FOR_PRE_REGISTRATION";
    app_id: string;
    store: "GOOGLE_APP_STORE" | "APPLE_APP_STORE";
    focus: "installs" | "in_app_actions" | "in_app_value";
    target_cpa: number | null;
    target_roas: number | null;
    ad_group_name: string;
    headlines: string[];
    descriptions: string[];
    images: AdImage[];
    videos: string[];
    /** The in-app conversion actions to bid for, by resource name. */
    conversion_actions: string[];
  };
  business: Record<string, unknown>;
};

export type StepId =
  | "goal"
  | "bidding"
  | "settings"
  | "ai_max"
  | "generation"
  | "ads"
  | "asset_group"
  | "ad_group"
  | "budget"
  | "review";

export type Problem = { step: StepId | string; words: string; blocks: boolean; code?: string };

export type SpecDraft = {
  id: string;
  v: 2;
  status: "draft" | "launched";
  spec: Spec;
  steps: { id: StepId; label: string }[];
  problems: Problem[];
  outcome: { refused?: string; created?: string[]; problems?: unknown[] } | null;
  campaign: string;
  created_at: string | null;
  /** PPCWay's checks on ad text the merchant typed, after a save. */
  advice?: { group: string; text: string; because: string }[];
};

export type ConversionGoal = {
  category: string;
  origin: string;
  biddable: boolean;
  label: string;
  origin_label?: string;
  actions: { name: string; status: string; primary: boolean; resource?: string; type?: string }[];
};

export type Setup = {
  connected: boolean;
  currency?: string;
  time_zone?: string;
  account_name?: string;
  business_name?: string;
  home?: Place | null;
  may_launch?: boolean;
  conversion?: { goals: ConversionGoal[]; tracking: boolean; reason?: string };
  trouble?: string;
  objectives: Record<Objective, { label: string; help: string; types: string[]; goals: boolean }>;
  types: Record<
    string,
    { label: string; help: string; creatable: boolean; why?: string; note?: string; needs?: string }
  >;
  steps: Record<string, StepId[]>;
  step_labels: Record<string, string>;
  /** The types PPCWay builds today. */
  built: string[];
  kinds?: {
    id: string;
    label: string;
    examples: string;
    noun: string;
    services_hint: string;
    win: string;
    promises: string[];
    negatives: string[];
  }[];
  promises?: { id: string; label: string; short: string }[];
};

/** Google's limits, from its help pages and the v25 reference. */
export const LIMITS = {
  headline: 30,
  description: 90,
  longHeadline: 90,
  path: 15,
  sitelinkText: 25,
  sitelinkLine: 35,
  callout: 25,
  snippetValue: 25,
  businessName: 25,
  headlinesMost: 15,
  descriptionsMost: 4,
  pmaxDescriptionsMost: 5,
  longHeadlinesMost: 5,
  adsPerGroup: 3,
  searchThemes: 50,
} as const;

export const MATCH_LABEL: Record<Match, string> = {
  BROAD: "Broad match",
  PHRASE: "Phrase match",
  EXACT: "Exact match",
};

/** How a keyword is written in Google's keyword box: broad, "phrase", [exact]. */
export function keywordText(k: Keyword): string {
  if (k.match === "PHRASE") return `"${k.text}"`;
  if (k.match === "EXACT") return `[${k.text}]`;
  return k.text;
}

/** Google's keyword box notation back into a keyword. */
export function parseKeyword(line: string): Keyword | null {
  const raw = line.trim();
  if (!raw) return null;
  if (raw.startsWith("[") && raw.endsWith("]"))
    return { text: raw.slice(1, -1).trim(), match: "EXACT" };
  if (raw.startsWith('"') && raw.endsWith('"'))
    return { text: raw.slice(1, -1).trim(), match: "PHRASE" };
  return { text: raw, match: "BROAD" };
}

export async function call<T>(path: string, body?: unknown): Promise<{ ok: boolean; data: T }> {
  const res = await fetch(`/api/campaigns/${path}`, {
    method: body === undefined ? "GET" : "POST",
    headers: body === undefined ? undefined : { "content-type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = (await res.json().catch(() => ({}))) as T;
  return { ok: res.ok, data };
}

/** The error a failed call said, in words. */
export function said(data: unknown, fallback = "That did not work."): string {
  const error = (data as { error?: unknown } | null)?.error;
  return typeof error === "string" ? error : fallback;
}
