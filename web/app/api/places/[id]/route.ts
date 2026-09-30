import { NextResponse } from "next/server";

/* One Google listing, read again through the backend so the key stays on the server. */
const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8300";

export async function GET(_request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  try {
    const res = await fetch(`${BACKEND}/v1/places/${encodeURIComponent(id)}`, {
      cache: "no-store",
    });
    const data = await res.json().catch(() => ({}));
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json({ error: "The business search is not reachable." }, { status: 503 });
  }
}
