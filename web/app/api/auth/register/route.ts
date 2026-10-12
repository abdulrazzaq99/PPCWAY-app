import { NextResponse } from "next/server";
import { SESSION_COOKIE, cookieOptions } from "@/lib/session";

/*
  Signing up with an address and a password. The token the backend hands back
  goes straight into an httpOnly cookie; the browser never holds it in script.
*/
const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8300";

async function signedIn(path: string, body: unknown): Promise<NextResponse> {
  try {
    const res = await fetch(`${BACKEND}${path}`, {
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
        { error: said.detail ?? "That did not work." },
        { status: res.status === 200 ? 400 : res.status },
      );
    }
    const reply = NextResponse.json({ person: said.person });
    reply.cookies.set(SESSION_COOKIE, said.token, cookieOptions);
    return reply;
  } catch {
    return NextResponse.json({ error: "The service is not reachable." }, { status: 503 });
  }
}

export async function POST(request: Request) {
  const body = await request.json().catch(() => null);
  if (!body) return NextResponse.json({ error: "Send the form as JSON." }, { status: 400 });
  return signedIn("/v1/auth/register", body);
}

export { signedIn };
