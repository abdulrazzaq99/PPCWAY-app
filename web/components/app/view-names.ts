/*
  The drawn states of each signed-in page, picked with `?view=` until the backend
  drives them. Plain module, no "use client", so server pages can read the arrays.
*/
export const OVERVIEW_VIEWS = [
  "calls",
  "spend",
  "paused-everyone",
  "support",
  "agency-view",
  "northgate",
  "week-one",
  "disconnected",
  "suspended",
  "card-declined",
  "no-tracking",
  "restaurant",
  "restricted",
] as const;
export type OverviewView = (typeof OVERVIEW_VIEWS)[number];

export const REPORT_VIEWS = ["report", "dates"] as const;
export type ReportView = (typeof REPORT_VIEWS)[number];

export const ACTIVITY_VIEWS = [
  "feed",
  "change",
  "refused",
  "outside-change",
  "headline-refused",
  "spike",
  "calls-down",
  "weak-headlines",
  "alerts",
  "emails",
  "batch",
  "switch-bidding",
] as const;
export type ActivityView = (typeof ACTIVITY_VIEWS)[number];

export const CAMPAIGN_VIEWS = [
  "list",
  "detail",
  "settings",
  "keywords",
  "search-terms",
  "ad-groups",
  "ads",
  "account",
  "add-keywords",
  "write-ad",
  "assets",
  "new",
  "website",
  "starter",
  "alerts",
  "built",
  "searches-why",
  "ads-rules",
  "why-shape",
  "pmax-logo",
  "pmax-month",
  "summit-plan",
  "summit-list",
  "summit-leaks",
  "summit-month",
  "summit-keywords",
  "summit-ad-test",
  "summit-results",
] as const;
export type CampaignView = (typeof CAMPAIGN_VIEWS)[number];

export const SETTINGS_VIEWS = [
  "autonomy",
  "autonomy-early",
  "full-auto",
  "plan",
  "team",
  "cancel",
  "delete",
  "business",
  "notifications",
  "two-step",
  "switch-plan",
  "payment-failed",
  "google",
  "results",
  "data",
  "owner-only",
  "your-data",
  "add-ons",
  "plan-owner-only",
] as const;
export type SettingsView = (typeof SETTINGS_VIEWS)[number];

export const AGENCY_VIEWS = ["overview", "add-client", "brand"] as const;
export type AgencyView = (typeof AGENCY_VIEWS)[number];

export const ADMIN_MERCHANT_VIEWS = ["list", "merchant", "change-log"] as const;
export const ADMIN_REVIEW_VIEWS = ["categories", "access", "block-list"] as const;
export const ADMIN_PLATFORM_VIEWS = ["platform", "rules"] as const;
export const ADMIN_METRIC_VIEWS = ["metrics", "ai"] as const;
