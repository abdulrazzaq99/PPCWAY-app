import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { SESSION_COOKIE } from "@/lib/session";

/* Ending every session, on every device. What you want when a laptop is lost. */
const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8300";

export async function POST() {
  const jar = await cookies();
  const token = jar.get(SESSION_COOKIE)?.value;
  if (!token) return NextResponse.json({ ended: 0 });
  try {
    const res = await fetch(`${BACKEND}/v1/auth/signout-everywhere`, {
      method: "POST",
      headers: { "x-session-token": token },
      cache: "no-store",
    });
    const said = (await res.json().catch(() => ({ ended: 0 }))) as { ended?: number };
    const reply = NextResponse.json(said, { status: res.status });
    // This browser is one of the devices, so its cookie goes too.
    reply.cookies.set(SESSION_COOKIE, "", { path: "/", maxAge: 0 });
    return reply;
  } catch {
    return NextResponse.json({ error: "The service is not reachable." }, { status: 503 });
  }
}
