import { NextResponse } from "next/server";

/*
  One way to hand a free-audit request to the backend.

  No session is read or sent: every door behind these paths is open to anybody
  by design, and what they give out is decided there, not here. The findings
  come back only from the verify and open doors, which is the whole point.
*/
const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8300";

export async function openly(
  path: string,
  options: { method?: string; body?: unknown } = {},
): Promise<NextResponse> {
  try {
    const res = await fetch(`${BACKEND}${path}`, {
      method: options.method ?? "GET",
      headers: options.body ? { "content-type": "application/json" } : undefined,
      body: options.body ? JSON.stringify(options.body) : undefined,
      cache: "no-store",
    });
    const said = (await res.json().catch(() => ({}))) as { detail?: unknown };
    if (!res.ok) {
      const detail = said.detail;
      return NextResponse.json(
        {
          error:
            typeof detail === "string"
              ? detail
              : Array.isArray(detail) && typeof detail[0] === "object"
                ? String(
                    (detail[0] as { msg?: string }).msg ?? "Check the highlighted fields.",
                  ).replace(/^Value error, /, "")
                : "That did not work.",
        },
        { status: res.status },
      );
    }
    return NextResponse.json(said);
  } catch {
    return NextResponse.json(
      { error: "We could not reach the audit service. Try again in a minute." },
      { status: 503 },
    );
  }
}

export async function sent(request: Request): Promise<unknown> {
  return request.json().catch(() => ({}));
}
