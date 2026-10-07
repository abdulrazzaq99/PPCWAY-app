import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { SESSION_COOKIE } from "@/lib/session";

/* The audits this person ran while signed in. Nobody signed in, nothing to show. */
const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8300";

export async function GET() {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) return NextResponse.json([], { status: 401 });
  try {
    const res = await fetch(`${BACKEND}/v1/audits/mine`, {
      headers: { "x-session-token": token },
      cache: "no-store",
    });
    if (!res.ok) return NextResponse.json([], { status: res.status });
    return NextResponse.json(await res.json());
  } catch {
    return NextResponse.json([], { status: 503 });
  }
}
