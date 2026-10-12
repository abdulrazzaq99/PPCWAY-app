import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { SESSION_COOKIE } from "@/lib/session";

/*
  One way to hand a request to the backend with the session on it. The browser
  never holds the token: it is in an httpOnly cookie, read here on the server.
*/
const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8300";

export async function pass(
  path: string,
  options: { method?: string; body?: unknown } = {},
): Promise<NextResponse> {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) return NextResponse.json({ error: "Sign in first." }, { status: 401 });
  try {
    const res = await fetch(`${BACKEND}${path}`, {
      method: options.method ?? "GET",
      headers: {
        "x-session-token": token,
        ...(options.body ? { "content-type": "application/json" } : {}),
      },
      body: options.body ? JSON.stringify(options.body) : undefined,
      cache: "no-store",
    });
    if (res.status === 204) return new NextResponse(null, { status: 204 });
    const said = (await res.json().catch(() => ({}))) as { detail?: string };
    if (!res.ok) {
      return NextResponse.json(
        { error: said.detail ?? "That did not work." },
        { status: res.status },
      );
    }
    return NextResponse.json(said);
  } catch {
    return NextResponse.json({ error: "The service is not reachable." }, { status: 503 });
  }
}
