import { NextResponse } from "next/server";

/* The same trade around that business, for the report's comparison card. */
const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8300";

export async function GET(request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  // A trade that hides its address has no coordinates on Google; the town is the anchor.
  const city = new URL(request.url).searchParams.get("city") ?? "";
  const query = new URLSearchParams({ limit: "6", city });
  try {
    const res = await fetch(`${BACKEND}/v1/places/${encodeURIComponent(id)}/nearby?${query}`, {
      cache: "no-store",
    });
    const data = await res.json().catch(() => ({}));
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json({ error: "The business search is not reachable." }, { status: 503 });
  }
}
