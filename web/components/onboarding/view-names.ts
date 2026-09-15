/*
  The drawn states of each onboarding step, keyed by `?view=`.
  Kept in a plain module so server pages can read the lists; the client view
  files import only the types.
*/
export const CONNECT_VIEWS = [
  "connect",
  "route",
  "pick",
  "accept",
  "accept-choice",
  "connected",
  "queue",
  "queue-full",
  "existing",
] as const;
export type ConnectViewName = (typeof CONNECT_VIEWS)[number];

export const BUSINESS_VIEWS = ["about", "basics", "money", "sources", "area", "manual"] as const;
export type BusinessViewName = (typeof BUSINESS_VIEWS)[number];

export const WEBSITE_VIEWS = ["running", "report", "finding"] as const;
export type WebsiteViewName = (typeof WEBSITE_VIEWS)[number];

export const CALLS_VIEWS = ["number", "verify", "tag", "sales", "existing", "quotes"] as const;
export type CallsViewName = (typeof CALLS_VIEWS)[number];

export const REVIEW_VIEWS = ["writing", "ready", "backup", "billing-done", "live"] as const;
export type ReviewViewName = (typeof REVIEW_VIEWS)[number];
