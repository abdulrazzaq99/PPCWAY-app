import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { SESSION_COOKIE } from "@/lib/session";

/* The consent screen's own words, and turning it on or off. */
const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8300";

async function pass(method: "GET" | "POST" | "DELETE") {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) return NextResponse.json({ error: "Sign in first." }, { status: 401 });
  try {
    const res = await fetch(`${BACKEND}/v1/otto/auto-apply`, {
      method,
      headers: { "x-session-token": token },
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

export const GET = () => pass("GET");
export const POST = () => pass("POST");
export const DELETE = () => pass("DELETE");
