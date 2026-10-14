import { pass } from "@/lib/pw-proxy";

/* Reading the account into the mirror: ask for a pass, and watch one happen. */
export async function POST() {
  return pass("/v1/ads/sync", { method: "POST" });
}

export async function GET() {
  return pass("/v1/ads/sync");
}
