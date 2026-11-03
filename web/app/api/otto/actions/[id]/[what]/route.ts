import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { SESSION_COOKIE } from "@/lib/session";

/*
  Approve, reject or undo one change. The action is addressed by id and the
  verb is in the path; the business it belongs to comes from the session on
  the server, never from here, so a card id from somewhere else resolves to
  nothing.
*/
const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8300";

const VERBS = new Set(["approve", "reject", "undo"]);

export async function POST(
  request: Request,
  { params }: { params: Promise<{ id: string; what: string }> },
) {
  const { id, what } = await params;
  if (!VERBS.has(what)) {
    return NextResponse.json({ error: "There is no such answer." }, { status: 404 });
  }
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) return NextResponse.json({ error: "Sign in first." }, { status: 401 });

  const body = what === "reject" ? await request.json().catch(() => ({})) : undefined;
  try {
    const res = await fetch(`${BACKEND}/v1/otto/actions/${id}/${what}`, {
      method: "POST",
      headers: {
        "x-session-token": token,
        ...(body ? { "content-type": "application/json" } : {}),
      },
      ...(body ? { body: JSON.stringify(body) } : {}),
      cache: "no-store",
    });
    const said = (await res.json().catch(() => ({}))) as { detail?: string };
    if (!res.ok) {
      return NextResponse.json(
        { error: said.detail ?? "That did not work." },
        { status: res.status },
      );
    }
    return NextResponse.json(said);
  } catch {
    return NextResponse.json({ error: "Otto is not reachable right now." }, { status: 503 });
  }
}
