import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { SESSION_COOKIE } from "@/lib/session";

/* The home and report numbers, read live from the merchant's own account. */
const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8300";

export async function GET(request: Request) {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) return NextResponse.json({ read: false }, { status: 401 });
  const days = new URL(request.url).searchParams.get("days") ?? "30";
  try {
    const res = await fetch(`${BACKEND}/v1/ads/summary?days=${encodeURIComponent(days)}`, {
      headers: { "x-session-token": token },
      cache: "no-store",
    });
    return NextResponse.json(await res.json(), { status: res.status });
  } catch {
    return NextResponse.json(
      { read: false, trouble: "The service is not reachable." },
      { status: 503 },
    );
  }
}
