import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { SESSION_COOKIE } from "@/lib/session";

/*
  What the connected Google Ads account says about the business it advertises,
  so the audit can stop asking for a name and a website it was already handed.
*/
const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8300";
const NOTHING = { connected: false, enough: false };

export async function GET() {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) return NextResponse.json(NOTHING);
  try {
    const res = await fetch(`${BACKEND}/v1/ads/business`, {
      headers: { "x-session-token": token },
      cache: "no-store",
    });
    if (!res.ok) return NextResponse.json(NOTHING);
    return NextResponse.json(await res.json());
  } catch {
    return NextResponse.json(NOTHING);
  }
}
