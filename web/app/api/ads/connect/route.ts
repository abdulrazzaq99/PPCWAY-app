import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { SESSION_COOKIE } from "@/lib/session";

/* Starts the trip to Google: the backend makes the state, we hand back the link. */
const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8300";

export async function POST() {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) return NextResponse.json({ error: "Sign in first." }, { status: 401 });
  try {
    const res = await fetch(`${BACKEND}/v1/ads/connect`, {
      method: "POST",
      headers: { "x-session-token": token },
      cache: "no-store",
    });
    const said = (await res.json().catch(() => ({}))) as { url?: string; detail?: string };
    if (!res.ok || !said.url) {
      return NextResponse.json(
        { error: said.detail ?? "Connecting Google Ads is not available right now." },
        { status: res.status },
      );
    }
    return NextResponse.json({ url: said.url });
  } catch {
    return NextResponse.json({ error: "The service is not reachable." }, { status: 503 });
  }
}
