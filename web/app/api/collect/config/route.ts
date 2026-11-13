import { NextResponse } from "next/server";

/*
  What the script should also tell Google Ads: the conversions the merchant
  chose to fire for a form and for a call. Public, from any site, and cached
  for a few minutes, since it changes only when the merchant changes it.
*/
const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8300";

const NOTHING = { tag: "", form: "", call: "" };

export async function GET(request: Request) {
  const key = (new URL(request.url).searchParams.get("k") ?? "").slice(0, 40);
  let said = NOTHING;
  if (key) {
    try {
      const res = await fetch(`${BACKEND}/v1/site/config?k=${encodeURIComponent(key)}`, {
        cache: "no-store",
      });
      if (res.ok) said = { ...NOTHING, ...((await res.json()) as typeof NOTHING) };
    } catch {
      // Nothing to fire, rather than an error on the merchant's page.
    }
  }
  return NextResponse.json(said, {
    headers: {
      "access-control-allow-origin": "*",
      "cache-control": "public, max-age=300",
    },
  });
}
