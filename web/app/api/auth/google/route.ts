import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { RAN_HERE_COOKIE, SESSION_COOKIE, cookieOptions } from "@/lib/session";

/*
  Google's token in, a session cookie out. The token is checked by the backend
  against Google's own keys; this route never trusts it on its own, and the
  session it gets back is put somewhere the page cannot read.
*/
const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8300";

export async function POST(request: Request) {
  const body = await request.json().catch(() => null);
  if (!body) return NextResponse.json({ error: "Send the token as JSON." }, { status: 400 });
  try {
    const res = await fetch(`${BACKEND}/v1/auth/google`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
      cache: "no-store",
    });
    const said = (await res.json().catch(() => ({}))) as {
      token?: string;
      person?: unknown;
      detail?: string;
    };
    if (!res.ok || !said.token) {
      return NextResponse.json(
        { error: said.detail ?? "Google signed you in, but we could not finish." },
        { status: res.status === 401 ? 401 : 502 },
      );
    }
    const reply = NextResponse.json({ person: said.person });
    reply.cookies.set(SESSION_COOKIE, said.token, cookieOptions);

    // The audits they ran here before signing in become theirs.
    const ran = ((await cookies()).get(RAN_HERE_COOKIE)?.value ?? "").split(",").filter(Boolean);
    if (ran.length) {
      await fetch(`${BACKEND}/v1/audits/claim`, {
        method: "POST",
        headers: { "content-type": "application/json", "x-session-token": said.token },
        body: JSON.stringify({ ids: ran }),
        cache: "no-store",
      }).catch(() => undefined);
      reply.cookies.delete(RAN_HERE_COOKIE);
    }
    return reply;
  } catch {
    return NextResponse.json({ error: "The sign-in service is not reachable." }, { status: 503 });
  }
}
