import { NextResponse } from "next/server";
import { signedIn } from "@/app/api/auth/register/route";

/* Setting a new password from the link in an email, which signs them in too. */
export async function POST(request: Request) {
  const body = await request.json().catch(() => null);
  if (!body) return NextResponse.json({ error: "Send the form as JSON." }, { status: 400 });
  return signedIn("/v1/auth/reset", body);
}
