import { NextResponse } from "next/server";

/*
  Asking for a six-digit sign-in code by email. Nothing is signed in here; the
  reply says only whether a code went, or how long to wait for the next. The
  backend answers the same for an address with an account and one without,
  because an unknown address is simply a sign-up.
*/
const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8300";

export async function POST(request: Request) {
  const body = await request.json().catch(() => null);
  if (!body) return NextResponse.json({ error: "Send the form as JSON." }, { status: 400 });
  try {
    const res = await fetch(`${BACKEND}/v1/auth/code`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ email: String(body.email ?? "") }),
      cache: "no-store",
    });
    const said = (await res.json().catch(() => ({}))) as {
      sent?: boolean;
      wait_seconds?: number;
      minutes?: number;
      detail?: unknown;
    };
    if (!res.ok) {
      // A malformed address comes back as a list of field errors; say it plainly.
      const error =
        typeof said.detail === "string" ? said.detail : "That does not look like an email address.";
      return NextResponse.json({ error }, { status: res.status });
    }
    return NextResponse.json({
      sent: Boolean(said.sent),
      wait_seconds: said.wait_seconds ?? 0,
      minutes: said.minutes ?? 10,
    });
  } catch {
    return NextResponse.json({ error: "The service is not reachable." }, { status: 503 });
  }
}
