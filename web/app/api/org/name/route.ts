import { NextResponse } from "next/server";
import { pass } from "@/lib/pw-proxy";

/* Renaming the business. It appears in invitations and in every report. */
export async function POST(request: Request) {
  const body = await request.json().catch(() => null);
  if (!body) return NextResponse.json({ error: "Nothing to send." }, { status: 400 });
  return pass("/v1/org/name", { method: "POST", body });
}
