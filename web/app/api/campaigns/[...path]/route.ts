import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { SESSION_COOKIE } from "@/lib/session";

/*
  The campaign builder's calls, passed to the API with the session attached.
  The browser holds no session token -- the cookie is httpOnly -- so every
  call goes through here. Only the builder's own paths are passed on, and the
  API decides who may do what; this route decides nothing.
*/
const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8300";

const ALLOWED = [
  /^start$/,
  /^places$/,
  /^languages$/,
  // The landing page's own name, read while the merchant types it.
  /^site$/,
  /^drafts$/,
  /^drafts\/[0-9a-f-]{36}$/,
  /^drafts\/[0-9a-f-]{36}\/launch$/,
];

async function pass(request: Request, path: string[]) {
  const joined = path.join("/");
  if (!ALLOWED.some((one) => one.test(joined))) {
    return NextResponse.json({ error: "There is no such page." }, { status: 404 });
  }
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) return NextResponse.json({ error: "Sign in first." }, { status: 401 });
  const query = new URL(request.url).search;
  const body = request.method === "POST" ? await request.text() : undefined;
  try {
    const res = await fetch(`${BACKEND}/v1/campaigns/${joined}${query}`, {
      method: request.method,
      headers: {
        "x-session-token": token,
        ...(body ? { "content-type": "application/json" } : {}),
      },
      ...(body ? { body } : {}),
      cache: "no-store",
    });
    const said = (await res.json().catch(() => ({}))) as { detail?: unknown };
    if (!res.ok) {
      const detail = typeof said.detail === "string" ? said.detail : "That did not work.";
      return NextResponse.json({ error: detail }, { status: res.status });
    }
    return NextResponse.json(said, { status: res.status });
  } catch {
    return NextResponse.json({ error: "PPCWay is not reachable right now." }, { status: 503 });
  }
}

export async function GET(request: Request, { params }: { params: Promise<{ path: string[] }> }) {
  return pass(request, (await params).path);
}

export async function POST(request: Request, { params }: { params: Promise<{ path: string[] }> }) {
  return pass(request, (await params).path);
}
