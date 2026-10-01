import { NextResponse } from "next/server";

/*
  What to offer while someone is still typing. The key stays on the server, and a
  dead list is an empty list: the form still works without suggestions.
*/
const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8300";

export async function GET(request: Request) {
  const asked = new URL(request.url).searchParams;
  const query = new URLSearchParams({ q: asked.get("q") ?? "", city: asked.get("city") ?? "" });
  try {
    const res = await fetch(`${BACKEND}/v1/places/suggest?${query}`, { cache: "no-store" });
    if (!res.ok) return NextResponse.json([]);
    return NextResponse.json(await res.json());
  } catch {
    return NextResponse.json([]);
  }
}
