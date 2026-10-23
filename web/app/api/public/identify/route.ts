import { openly, sent } from "@/lib/public-proxy";

/* What sort of business this looks like, before anything is checked. */
export async function POST(request: Request) {
  return openly("/v1/public/identify", { method: "POST", body: await sent(request) });
}
