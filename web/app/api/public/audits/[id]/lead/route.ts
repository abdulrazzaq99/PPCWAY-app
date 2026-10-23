import { openly, sent } from "@/lib/public-proxy";

/* Who asked, and a code posted to them. */
export async function POST(request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return openly(`/v1/public/audits/${encodeURIComponent(id)}/lead`, {
    method: "POST",
    body: await sent(request),
  });
}
