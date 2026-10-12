import { NextResponse } from "next/server";
import { pass } from "@/lib/pw-proxy";

export async function POST(request: Request) {
  const body = await request.json().catch(() => null);
  if (!body) return NextResponse.json({ error: "Nothing to send." }, { status: 400 });
  return pass("/v1/org/role", { method: "POST", body });
}

export async function DELETE(request: Request) {
  const id = new URL(request.url).searchParams.get("account_id");
  if (!id) return NextResponse.json({ error: "Who?" }, { status: 400 });
  return pass(`/v1/org/people/${encodeURIComponent(id)}`, { method: "DELETE" });
}
