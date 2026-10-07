import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { SESSION_COOKIE } from "@/lib/session";

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
    const data = await res.json().catch(() => ({}));
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json(
      { error: "The audit service is not reachable right now. Try again in a minute." },
      { status: 503 },
    );
  }
}
