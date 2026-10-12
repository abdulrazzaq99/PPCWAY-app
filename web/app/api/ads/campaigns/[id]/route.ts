import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { SESSION_COOKIE } from "@/lib/session";

/* One campaign, with its keywords, search terms and ads. */
const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8300";

export async function GET(request: Request, context: { params: Promise<{ id: string }> }) {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) return NextResponse.json({ read: false }, { status: 401 });
  const { id } = await context.params;
  const days = new URL(request.url).searchParams.get("days") ?? "30";
  try {
    const res = await fetch(
      `${BACKEND}/v1/ads/campaigns/${encodeURIComponent(id)}?days=${encodeURIComponent(days)}`,
      { headers: { "x-session-token": token }, cache: "no-store" },
    );
    return NextResponse.json(await res.json(), { status: res.status });
  } catch {
    return NextResponse.json(
      { read: false, trouble: "The service is not reachable." },
      { status: 503 },
    );
  }
}
