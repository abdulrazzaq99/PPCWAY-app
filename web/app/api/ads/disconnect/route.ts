import { pass } from "@/lib/pw-proxy";

/* Ending the Google Ads permission, and destroying the stored key with it. */
export async function POST() {
  return pass("/v1/ads/disconnect", { method: "POST" });
}
