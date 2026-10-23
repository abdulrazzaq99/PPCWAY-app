import { NextResponse, type NextRequest } from "next/server";

/*
  A password gate for the deployment. When SITE_PASSWORD is set, every page and
  API route needs the gate cookie, which /api/gate sets after the right password.
  Without SITE_PASSWORD (local development) nothing is gated. The cookie holds a
  hash of the password, never the password, so rotating the password logs
  everyone out.

  Three pages stay open whatever the password is, because Google's OAuth consent
  screen names them: app.ppcway.com is the registered application home page, and
  /privacy and /terms are the registered policy links. App verification is in
  review, and a reviewer who finds a password where the privacy policy should be
  has every reason to refuse us. They are also the three pages with nothing on
  them worth hiding.
*/
/*
  Open, password or no password.

  The free audit is the launched part: a stranger types their business name,
  gets a real report, and can have it emailed as a PDF, all without an account
  and without knowing any password. Everything it touches is listed here —
  the screens, the run, the polling, the screenshots, the PDF, the email, and
  the Google Maps lookups behind the name field. Miss one and the audit breaks
  for exactly the people it was opened for.

  The rest: `/`, `/privacy` and `/terms` are the pages Google's reviewers read
  and the ones its consent screen names; `/r` and `/fixes` are the shared
  links, which exist precisely so somebody with no account — an accountant, a
  web developer — can read one thing.
*/
const OPEN = [
  "/gate",
  "/api/gate",
  "/",
  "/privacy",
  "/terms",
  "/r",
  "/fixes",
  // The free audit, end to end.
  "/audit",
  "/api/audit",
  "/api/places",
  "/api/public",
];

/*
  The signed-in screens. Without a session they send people to sign in rather than
  showing the sample data they were drawn with. `?view=` is the exception: it is
  how the Figma states are reviewed, and it says plainly that it is a drawing.
*/
const SIGNED_IN_ONLY = [
  "/home",
  "/campaigns",
  "/reports",
  "/otto",
  "/chat",
  "/welcome",
  "/tools",
  "/settings",
  "/invite",
  "/overview",
  "/activity",
  "/approvals",
  "/campaigns",
  "/searches",
  "/settings",
  "/agency",
  "/admin",
  "/audit/mine",
];
const SESSION_COOKIE = "ppcway_session";

/*
  One address, once CANONICAL_HOST is set. A session cookie belongs to the host
  that set it, so somebody who signs in on the Cloud Run address and comes back
  from Google on the domain arrives as a stranger, with no session and no
  explanation. Rather than keep both hosts working and hope nobody mixes them,
  everything is sent to the one host. Unset locally, where the host is localhost.
*/
const CANONICAL = process.env.CANONICAL_HOST;

function wrongHost(request: NextRequest): string | null {
  if (!CANONICAL) return null;
  const host = request.headers.get("host");
  if (!host || host === CANONICAL || host.startsWith("localhost")) return null;
  return CANONICAL;
}

function needsSignIn(request: NextRequest): boolean {
  const { pathname, searchParams } = request.nextUrl;
  if (searchParams.has("view")) return false;
  if (!SIGNED_IN_ONLY.some((p) => pathname === p || pathname.startsWith(p + "/"))) return false;
  return !request.cookies.get(SESSION_COOKIE)?.value;
}

async function expectedToken(password: string): Promise<string> {
  const bytes = new TextEncoder().encode(`ppcway-gate:${password}`);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest), (b) => b.toString(16).padStart(2, "0")).join("");
}

/*
  The cookie rolls forward with the session behind it. The backend renews the
  session when it is used; without this the browser would still throw the cookie
  away thirty days after sign-in, and somebody here every day would be signed
  out anyway — which is the bug this pairs with, not a separate nicety.
*/
function keepSignedIn(request: NextRequest, reply: NextResponse): NextResponse {
  const token = request.cookies.get(SESSION_COOKIE)?.value;
  if (token) {
    reply.cookies.set(SESSION_COOKIE, token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      path: "/",
      maxAge: 60 * 60 * 24 * 30,
    });
  }
  return reply;
}

/*
  Carry the path on to the page.

  It has to go on the REQUEST, not the reply: `headers()` in a server component
  reads what came in, so a header set on the way out is invisible to it. Setting
  it on the reply is why the sidebar marked Home on every screen — the layout
  asked where it was, got nothing, and fell back to Home.
*/
function onward(request: NextRequest): NextResponse {
  const asked = new Headers(request.headers);
  asked.set("x-pathname", request.nextUrl.pathname + request.nextUrl.search);
  return NextResponse.next({ request: { headers: asked } });
}

export async function proxy(request: NextRequest) {
  const canonical = wrongHost(request);
  if (canonical) {
    const url = request.nextUrl.clone();
    url.protocol = "https:";
    url.host = canonical;
    url.port = "";
    return NextResponse.redirect(url, 308);
  }

  const password = process.env.SITE_PASSWORD;
  const { pathname, search } = request.nextUrl;
  const open = OPEN.some((p) => pathname === p || pathname.startsWith(p + "/"));
  if (password && !open) {
    const token = request.cookies.get("ppcway_gate")?.value;
    if (!token || token !== (await expectedToken(password))) {
      if (pathname.startsWith("/api/")) {
        return NextResponse.json({ error: "This site is not open yet." }, { status: 401 });
      }
      const url = request.nextUrl.clone();
      url.pathname = "/gate";
      url.search = "";
      url.searchParams.set("next", pathname + search);
      return NextResponse.redirect(url);
    }
  }

  if (needsSignIn(request)) {
    const url = request.nextUrl.clone();
    const asked = url.pathname + url.search;
    url.pathname = "/login";
    url.search = "";
    url.searchParams.set("next", asked);
    return NextResponse.redirect(url);
  }

  return keepSignedIn(request, onward(request));
}

export const config = {
  // Everything except Next's own assets and static files.
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:png|jpg|jpeg|gif|svg|ico|webp|txt|xml)$).*)",
  ],
};
