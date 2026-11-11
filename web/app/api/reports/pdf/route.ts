import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { SESSION_COOKIE } from "@/lib/session";

/*
  The report as a PDF, passed through as the bytes the backend printed. The
  JSON proxy cannot carry a file, so this one route streams instead; the
  session still travels only in the httpOnly cookie, read here on the server.
*/
const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8300";
const PERIODS = new Set(["7", "30", "90"]);

export async function GET(request: Request) {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) return NextResponse.json({ error: "Sign in first." }, { status: 401 });
  const asked = new URL(request.url).searchParams.get("days") ?? "30";
  const days = PERIODS.has(asked) ? asked : "30";
  try {
    const res = await fetch(`${BACKEND}/v1/reports/pdf?days=${days}`, {
      headers: { "x-session-token": token },
      cache: "no-store",
    });
    if (!res.ok || !res.body) {
      const said = (await res.json().catch(() => ({}))) as { detail?: string };
      return NextResponse.json(
        { error: said.detail ?? "The PDF could not be made just now." },
        { status: res.status || 502 },
      );
    }
    return new Response(res.body, {
      status: 200,
      headers: {
        "content-type": "application/pdf",
        "content-disposition":
          res.headers.get("content-disposition") ?? 'attachment; filename="PPCWay report.pdf"',
        "cache-control": "no-store",
      },
    });
  } catch {
    return NextResponse.json({ error: "We could not reach the service." }, { status: 502 });
  }
}
