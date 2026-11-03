import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { SESSION_COOKIE } from "@/lib/session";

/* The cards Otto has for this business. Read-only; it changes nothing. */
const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8300";

export async function GET() {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) return NextResponse.json({ error: "Sign in first." }, { status: 401 });
  try {
    const res = await fetch(`${BACKEND}/v1/otto/inbox`, {
      headers: { "x-session-token": token },
      cache: "no-store",
    });
    return NextResponse.json(await res.json().catch(() => ({})), { status: res.status });
  } catch {
    return NextResponse.json({ error: "Otto is not reachable right now." }, { status: 503 });
  }
}
