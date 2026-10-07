import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { SESSION_COOKIE } from "@/lib/session";

/* The advertising accounts their permission reaches. */
const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8300";

export async function GET() {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) return NextResponse.json({ accounts: [], error: "Sign in first." }, { status: 401 });
  try {
    const res = await fetch(`${BACKEND}/v1/ads/accounts`, {
      headers: { "x-session-token": token },
      cache: "no-store",
    });
    const said = await res.json().catch(() => ({}));
    if (!res.ok) {
      return NextResponse.json(
        { accounts: [], error: (said as { detail?: string }).detail ?? "Google would not answer." },
        { status: res.status },
      );
    }
    return NextResponse.json({ accounts: said });
  } catch {
    return NextResponse.json(
      { accounts: [], error: "The service is not reachable." },
      { status: 503 },
    );
  }
}
