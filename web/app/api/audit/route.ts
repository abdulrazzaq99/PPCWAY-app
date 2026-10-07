import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { RAN_HERE_COOKIE, RAN_HERE_KEEP, SESSION_COOKIE, cookieOptions } from "@/lib/session";

/*
  The public audit form posts here; this forwards to the backend so its address
  and any future key stay on the server. BACKEND_URL defaults to the local API.
*/
const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8300";

export async function POST(request: Request) {
  const body = await request.json().catch(() => null);
  if (!body) return NextResponse.json({ error: "Send the form as JSON." }, { status: 400 });
  try {
    // Signed in, the run is kept against the account; signed out, the header is absent.
    const token = (await cookies()).get(SESSION_COOKIE)?.value;
    const res = await fetch(`${BACKEND}/v1/audits`, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        ...(token ? { "x-session-token": token } : {}),
      },
      body: JSON.stringify(body),
      cache: "no-store",
    });
    const data = (await res.json().catch(() => ({}))) as { id?: string };
    const reply = NextResponse.json(data, { status: res.status });
    if (res.ok && data.id && !token) {
      // Signed out: remember it here so it can follow them into an account later.
      const jar = await cookies();
      const ran = (jar.get(RAN_HERE_COOKIE)?.value ?? "").split(",").filter(Boolean);
      const kept = [data.id, ...ran.filter((id) => id !== data.id)].slice(0, RAN_HERE_KEEP);
      reply.cookies.set(RAN_HERE_COOKIE, kept.join(","), { ...cookieOptions, httpOnly: true });
    }
    return reply;
  } catch {
    return NextResponse.json(
      { error: "The audit service is not reachable right now. Try again in a minute." },
      { status: 503 },
    );
  }
}
