/*
  Google listings, read through the backend so the Maps key stays on the server.
  Server components only: it reads BACKEND_URL, which the browser never sees.
  Only the place id may be kept, so every screen that shows a listing reads it
  again from here rather than from anything we stored.
*/
import type { Listing } from "./listing";

const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8300";
const UNREACHABLE = "We could not reach the business search just now. Try again in a minute.";
const SPENT =
  "The day's allowance for looking businesses up on Google is used up. The website check still works.";

export async function searchListings(
  name: string,
  city: string,
): Promise<{ listings: Listing[]; error?: string }> {
  const query = new URLSearchParams({ name, city });
  try {
    const res = await fetch(`${BACKEND}/v1/places/search?${query}`, { cache: "no-store" });
    if (!res.ok) {
      return {
        listings: [],
        error:
          res.status === 429
            ? SPENT
            : res.status === 503
              ? "Business search is not switched on yet."
              : UNREACHABLE,
      };
    }
    return { listings: (await res.json()) as Listing[] };
  } catch {
    return { listings: [], error: UNREACHABLE };
  }
}

export async function readListing(placeId: string): Promise<Listing | null> {
  try {
    const res = await fetch(`${BACKEND}/v1/places/${encodeURIComponent(placeId)}`, {
      cache: "no-store",
    });
    return res.ok ? ((await res.json()) as Listing) : null;
  } catch {
    return null;
  }
}
