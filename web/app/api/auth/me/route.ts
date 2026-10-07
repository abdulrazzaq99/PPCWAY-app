import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { SESSION_COOKIE } from "@/lib/session";

/* Who is signed in, for the header. Nobody signed in is a 401, not an error. */
const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8300";

export async function GET() {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) return NextResponse.json({ person: null }, { status: 401 });
  try {
    const res = await fetch(`${BACKEND}/v1/auth/me`, {
      headers: { "x-session-token": token },
      cache: "no-store",
    });
    if (!res.ok) return NextResponse.json({ person: null }, { status: 401 });
    return NextResponse.json({ person: await res.json() });
  } catch {
    return NextResponse.json({ person: null }, { status: 503 });
  }
}
