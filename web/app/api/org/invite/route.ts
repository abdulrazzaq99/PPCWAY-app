import { NextResponse } from "next/server";
import { pass } from "@/lib/pw-proxy";

export async function POST(request: Request) {
  const body = await request.json().catch(() => null);
  if (!body) return NextResponse.json({ error: "Nothing to send." }, { status: 400 });
  return pass("/v1/org/invite", { method: "POST", body });
}
