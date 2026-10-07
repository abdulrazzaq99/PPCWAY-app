import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { SESSION_COOKIE } from "@/lib/session";

/* Sign out here: the backend revokes the session, and the cookie goes. */
const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8300";

export async function POST() {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (token) {
    try {
      await fetch(`${BACKEND}/v1/auth/signout`, {
        method: "POST",
        headers: { "x-session-token": token },
        cache: "no-store",
      });
    } catch {
      /* the cookie goes either way: a session nobody can reach is already over */
    }
  }
  const reply = NextResponse.json({ ok: true });
  reply.cookies.delete(SESSION_COOKIE);
  return reply;
}
