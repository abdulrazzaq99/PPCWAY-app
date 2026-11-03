import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { SESSION_COOKIE } from "@/lib/session";

/*
  A question to Otto, streamed straight back. A pass-through: the body goes up
  and the server-sent events come down untouched, because the status lines are
  only worth having if they arrive while the lookup is running rather than all
  at once with the answer.

  `no-transform` and `X-Accel-Buffering: no` are carried forward deliberately.
  A proxy that buffers this stream turns four seconds of "reading what people
  searched for" into four seconds of nothing, which is worse than not having
  the lines at all.
*/
const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8300";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) return NextResponse.json({ error: "Sign in first." }, { status: 401 });
  const body = await request.json().catch(() => null);
  if (!body) return NextResponse.json({ error: "Ask something." }, { status: 400 });

  try {
    const res = await fetch(`${BACKEND}/v1/otto/ask`, {
      method: "POST",
      headers: { "content-type": "application/json", "x-session-token": token },
      body: JSON.stringify(body),
      cache: "no-store",
    });
    if (!res.ok || !res.body) {
      const said = (await res.json().catch(() => ({}))) as { detail?: string };
      return NextResponse.json(
        { error: said.detail ?? "Otto could not answer that." },
        { status: res.status },
      );
    }
    return new Response(res.body, {
      status: 200,
      headers: {
        "content-type": "text/event-stream",
        "cache-control": "no-cache, no-transform",
        "x-accel-buffering": "no",
      },
    });
  } catch {
    return NextResponse.json({ error: "Otto is not reachable right now." }, { status: 503 });
  }
}
