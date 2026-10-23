import { openly, sent } from "@/lib/public-proxy";

/* Six digits, and then everything. */
export async function POST(request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return openly(`/v1/public/audits/${encodeURIComponent(id)}/verify`, {
    method: "POST",
    body: await sent(request),
  });
}
