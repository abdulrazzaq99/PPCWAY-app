import { NextResponse } from "next/server";
import { pass } from "@/lib/pw-proxy";

/* The fix list, to whoever looks after the website. */
export async function POST(request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const body = await request.json().catch(() => ({}));
  if (!id) return NextResponse.json({ error: "Which audit?" }, { status: 400 });
  return pass(`/v1/audits/${encodeURIComponent(id)}/share`, { method: "POST", body: body ?? {} });
}
