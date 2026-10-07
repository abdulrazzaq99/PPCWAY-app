import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { SESSION_COOKIE } from "@/lib/session";

/* Whether this person has connected Google Ads, for the signed-in home. */
const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8300";

export async function GET() {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) return NextResponse.json({ connected: false }, { status: 401 });
  try {
    const res = await fetch(`${BACKEND}/v1/ads/status`, {
      headers: { "x-session-token": token },
      cache: "no-store",
    });
    if (!res.ok) return NextResponse.json({ connected: false }, { status: res.status });
    return NextResponse.json(await res.json());
  } catch {
    return NextResponse.json({ connected: false }, { status: 503 });
  }
}
