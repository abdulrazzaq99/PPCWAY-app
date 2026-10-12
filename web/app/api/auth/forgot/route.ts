import { NextResponse } from "next/server";

/*
  Asking for a reset link. It always answers the same, because whether an
  address has an account is not a stranger's business.
*/
const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8300";

export async function POST(request: Request) {
  const body = await request.json().catch(() => null);
  if (!body) return NextResponse.json({ error: "Send the form as JSON." }, { status: 400 });
  try {
    await fetch(`${BACKEND}/v1/auth/forgot`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
      cache: "no-store",
    });
  } catch {
    // Even a failure here says nothing to the caller.
  }
  return new NextResponse(null, { status: 204 });
}
