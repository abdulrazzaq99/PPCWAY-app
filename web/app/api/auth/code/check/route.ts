import { NextResponse } from "next/server";
import { signedIn } from "@/app/api/auth/register/route";

/* The six digits from the email. Right, and the session goes into the cookie. */
export async function POST(request: Request) {
  const body = await request.json().catch(() => null);
  if (!body) return NextResponse.json({ error: "Send the form as JSON." }, { status: 400 });
  return signedIn("/v1/auth/code/check", {
    email: String(body.email ?? ""),
    code: String(body.code ?? ""),
    name: String(body.name ?? ""),
  });
}
