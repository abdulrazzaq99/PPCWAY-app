import { openly } from "@/lib/public-proxy";

/* Where the run has got to, and the score once it is done. Never the findings. */
export async function GET(_request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return openly(`/v1/public/audits/${encodeURIComponent(id)}`);
}
