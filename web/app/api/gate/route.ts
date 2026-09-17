import { NextResponse } from "next/server";

async function expectedToken(password: string): Promise<string> {
  const bytes = new TextEncoder().encode(`ppcway-gate:${password}`);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest), (b) => b.toString(16).padStart(2, "0")).join("");
}

function same(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

export async function POST(request: Request) {
  const password = process.env.SITE_PASSWORD;
  if (!password) return NextResponse.json({ ok: true });
  const body = (await request.json().catch(() => ({}))) as { password?: string };
  const given = typeof body.password === "string" ? body.password : "";
  if (!same(given, password)) {
    return NextResponse.json({ error: "That is not the password." }, { status: 401 });
  }
  const res = NextResponse.json({ ok: true });
  res.cookies.set("ppcway_gate", await expectedToken(password), {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: 60 * 60 * 24 * 30,
  });
  return res;
}
