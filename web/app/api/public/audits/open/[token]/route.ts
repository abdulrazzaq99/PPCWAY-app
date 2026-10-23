import { openly } from "@/lib/public-proxy";

/* The link in the email, which opens the report on any device. */
export async function GET(_request: Request, { params }: { params: Promise<{ token: string }> }) {
  const { token } = await params;
  return openly(`/v1/public/audits/open/${encodeURIComponent(token)}`);
}
