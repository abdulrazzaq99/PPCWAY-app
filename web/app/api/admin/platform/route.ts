import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { SESSION_COOKIE } from "@/lib/session";

/*
  Stopping and releasing writes from the panel.

  The backend checks the caller's level again; this route does not decide
  anything. It exists because the browser holds no session token -- the cookie
  is httpOnly, which is the point -- so every call to the API goes through
  here.
*/
const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8300";

export async function POST(request: Request) {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) return NextResponse.json({ error: "Sign in first." }, { status: 401 });
  const body = (await request.json().catch(() => ({}))) as {
    doing?: string;
    customer_id?: string;
    because?: string;
  };
  const where = body.doing === "release" ? "release" : "stop";
  try {
    const res = await fetch(`${BACKEND}/v1/admin/platform/${where}`, {
      method: "POST",
      headers: { "content-type": "application/json", "x-session-token": token },
      body: JSON.stringify({
        customer_id: body.customer_id ?? "",
        because: body.because ?? "",
      }),
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
    return NextResponse.json({ error: "The API is not reachable." }, { status: 503 });
  }
}
