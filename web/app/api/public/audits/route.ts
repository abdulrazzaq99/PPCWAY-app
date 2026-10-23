import { openly, sent } from "@/lib/public-proxy";

/* Start a free audit. Open to anybody, no account, no password. */
export async function POST(request: Request) {
  return openly("/v1/public/audits", { method: "POST", body: await sent(request) });
}
