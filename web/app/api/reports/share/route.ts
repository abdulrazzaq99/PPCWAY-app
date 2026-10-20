import { NextResponse } from "next/server";
import { pass } from "@/lib/pw-proxy";

/* A link to the report that needs no login, and the way to stop it working. */
export async function POST(request: Request) {
  const body = await request.json().catch(() => ({}));
  return pass("/v1/reports/share", { method: "POST", body: body ?? {} });
}

export async function DELETE(request: Request) {
  const id = new URL(request.url).searchParams.get("id");
  if (!id) return NextResponse.json({ error: "Which link?" }, { status: 400 });
  return pass(`/v1/reports/share/${encodeURIComponent(id)}`, { method: "DELETE" });
}
