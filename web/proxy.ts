import { NextResponse, type NextRequest } from "next/server";

/*
  A password gate for the preview deployment. When SITE_PASSWORD is set, every
  page and API route needs the gate cookie, which /api/gate sets after the right
  password. Without SITE_PASSWORD (local development) nothing is gated.
  The cookie holds a hash of the password, never the password, so rotating the
  password logs everyone out.
*/
const OPEN = ["/gate", "/api/gate"];

async function expectedToken(password: string): Promise<string> {
  const bytes = new TextEncoder().encode(`ppcway-gate:${password}`);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest), (b) => b.toString(16).padStart(2, "0")).join("");
}

export async function proxy(request: NextRequest) {
  const password = process.env.SITE_PASSWORD;
  if (!password) return NextResponse.next();
  const { pathname, search } = request.nextUrl;
  if (OPEN.some((p) => pathname === p || pathname.startsWith(p + "/"))) return NextResponse.next();
  const token = request.cookies.get("ppcway_gate")?.value;
  if (token && token === (await expectedToken(password))) return NextResponse.next();
  if (pathname.startsWith("/api/")) {
    return NextResponse.json({ error: "This preview is password protected." }, { status: 401 });
  }
  const url = request.nextUrl.clone();
  url.pathname = "/gate";
  url.search = "";
  url.searchParams.set("next", pathname + search);
  return NextResponse.redirect(url);
}

export const config = {
  // Everything except Next's own assets and static files.
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:png|jpg|jpeg|gif|svg|ico|webp|txt|xml)$).*)",
  ],
};
