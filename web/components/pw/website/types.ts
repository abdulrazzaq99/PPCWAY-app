/* What the Website screen reads from the API. See backend `ppcway.site`. */

export type SiteSetup = {
  key: string;
  snippet: string;
  script_url: string;
  installed: boolean;
  last_seen_at: string | null;
  last_seen_url: string;
  send_jobs: boolean;
  job_action: string;
  form_send_to: string;
  call_send_to: string;
  connected: boolean;
  currency: string;
  may_change: boolean;
};

export type SiteStats = {
  days: number;
  visits: number;
  leads: number;
  rate: number | null;
  kinds: { form: number; call: number; email: number };
  jobs: number;
  jobs_value: number;
  by_day: { day: string; visits: number; leads: number }[];
  sources: { source: string; label: string; visits: number; leads: number }[];
  pages: { page: string; visits: number; leads: number }[];
};

export type Lead = {
  id: string;
  created_at: string;
  kind: "form" | "call" | "email";
  page: string;
  form: string;
  fields: [string, string][];
  name: string;
  email: string;
  phone: string;
  source: string;
  source_label: string;
  campaign: string;
  from_ad: boolean;
  status: "new" | "job" | "not_job" | "spam";
  value: number | null;
  currency: string;
  upload: "" | "waiting" | "sent" | "failed" | "no_click";
  upload_note: string;
};

export type Choice = { name: string; category: string; send_to: string };
