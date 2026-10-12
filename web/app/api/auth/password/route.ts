import { NextResponse } from "next/server";
import { signedIn } from "@/app/api/auth/register/route";

/* Signing in with an address and a password. */
export async function POST(request: Request) {
  const body = await request.json().catch(() => null);
  if (!body) return NextResponse.json({ error: "Send the form as JSON." }, { status: 400 });
  return signedIn("/v1/auth/password", body);
}
