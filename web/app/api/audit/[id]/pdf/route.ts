import { NextResponse } from "next/server";

/*
  The report as a file. The backend prints it with the same headless browser the
  audit already uses, so what downloads is the page itself rather than a second
  layout built to resemble it.

  The bytes are passed straight through rather than buffered here: a report with
  screenshots in it is a few megabytes, and there is nothing to inspect.
*/
const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8300";
const FALLBACK = 'attachment; filename="PPCWay audit.pdf"';

export async function GET(_request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  if (!id) return NextResponse.json({ error: "Which audit?" }, { status: 400 });
  try {
    const res = await fetch(`${BACKEND}/v1/audits/${encodeURIComponent(id)}/pdf`, {
      cache: "no-store",
    });
    if (!res.ok) {
      const said = (await res.json().catch(() => ({}))) as { detail?: string };
      return NextResponse.json(
        { error: said.detail ?? "That report could not be printed." },
        { status: res.status },
      );
    }
    return new NextResponse(res.body, {
      status: 200,
      headers: {
        "content-type": "application/pdf",
        "content-disposition": res.headers.get("content-disposition") ?? FALLBACK,
      },
    });
  } catch {
    return NextResponse.json(
      { error: "The audit service is not reachable right now." },
      { status: 503 },
    );
  }
}
