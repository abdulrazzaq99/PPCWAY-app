import { openly } from "@/lib/public-proxy";

/* Another code, unless one went out moments ago. */
export async function POST(_request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return openly(`/v1/public/audits/${encodeURIComponent(id)}/resend`, {
    method: "POST",
    body: {},
  });
}
