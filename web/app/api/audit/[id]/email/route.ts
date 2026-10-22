import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { SESSION_COOKIE } from "@/lib/session";

/*
  Send a finished audit to an inbox.

  Not `pass()` from lib/pw-proxy, which refuses without a session: the free
  audit is the funnel, and somebody who has not signed up yet is exactly who
  asks for it by email. The session goes on when there is one, and the backend
  prefers it over anything the body says.
*/
const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8300";

export async function POST(request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  if (!id) return NextResponse.json({ error: "Which audit?" }, { status: 400 });
  const body = await request.json().catch(() => ({}));
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  try {
    const res = await fetch(`${BACKEND}/v1/audits/${encodeURIComponent(id)}/email`, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        ...(token ? { "x-session-token": token } : {}),
      },
      body: JSON.stringify(body ?? {}),
      cache: "no-store",
    });
    const said = (await res.json().catch(() => ({}))) as { detail?: string };
    if (!res.ok) {
      return NextResponse.json(
        { error: said.detail ?? "That could not be sent." },
        { status: res.status },
      );
    }
    return NextResponse.json(said);
  } catch {
    return NextResponse.json(
      { error: "The audit service is not reachable right now." },
      { status: 503 },
    );
  }
}
