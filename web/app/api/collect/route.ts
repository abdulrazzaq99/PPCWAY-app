import { NextResponse } from "next/server";

/*
  Where the PPCWay script on a merchant's website reports, from any site, so it
  answers every origin. It holds no cookie and reads none: the script's key
  says which business, and the backend trusts nothing else about the event.

  The script sends plain text (a "simple" request, so the browser asks no
  permission first and sendBeacon works). Passed on with the visitor's address
  and browser, which the backend uses only to count and to turn robots away.
*/
const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8300";

const OPEN = {
  "access-control-allow-origin": "*",
  "access-control-allow-methods": "POST, OPTIONS",
  "access-control-allow-headers": "content-type",
  "access-control-max-age": "86400",
};

export async function OPTIONS() {
  return new NextResponse(null, { status: 204, headers: OPEN });
}

export async function POST(request: Request) {
  const body = await request.text().catch(() => "");
  if (body && body.length <= 20_000) {
    const forwarded = request.headers.get("x-forwarded-for") ?? "";
    try {
      await fetch(`${BACKEND}/v1/site/collect`, {
        method: "POST",
        headers: {
          "content-type": "application/json",
          "x-visitor-address": forwarded.split(",")[0].trim().slice(0, 100),
          "x-visitor-agent": (request.headers.get("user-agent") ?? "").slice(0, 400),
        },
        body,
        cache: "no-store",
      });
    } catch {
      // The visitor's page must never notice PPCWay being away.
    }
  }
  return new NextResponse(null, { status: 204, headers: OPEN });
}
