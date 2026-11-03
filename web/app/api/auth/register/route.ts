import { NextResponse } from "next/server";
import { SESSION_COOKIE, cookieOptions } from "@/lib/session";

/*
  Signing up with an address and a password. The token the backend hands back
  goes straight into an httpOnly cookie; the browser never holds it in script.
*/
const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8300";

/*
  Where this person belongs once they are in.

  Asked here rather than offered on the login page. A "sign in as staff" option
  would have to be visible to everybody who can see the login form -- every
  merchant and every stranger -- and it would tell all of them that an internal
  panel exists and roughly where. Who somebody is, is already known the moment
  they sign in, so there is nothing to ask them.

  `whoami` answers 200 with `staff: false` for everybody else, so this costs
  one quick request at sign-in and never fails a sign-in: if it cannot be
  reached, the person lands on their own dashboard, which is where almost
  everybody belongs anyway.
*/
async function landingFor(token: string): Promise<string> {
  try {
    const res = await fetch(`${BACKEND}/v1/admin/whoami`, {
      headers: { "x-session-token": token },
      cache: "no-store",
    });
    if (!res.ok) return "/home";
    const said = (await res.json().catch(() => ({}))) as { staff?: boolean };
    return said.staff ? "/admin" : "/home";
  } catch {
    return "/home";
  }
}

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
    const reply = NextResponse.json({
      person: said.person,
      landing: await landingFor(said.token),
    });
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

export { landingFor, signedIn };
