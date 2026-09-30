/*
  A Google listing as the backend hands it over, and the two sentences the screens
  make of it. No server bindings here: the find screens are client components, so
  the fetching lives in `listings.ts` and only this file crosses over.
*/
export type Listing = {
  place_id: string;
  name: string;
  address: string;
  category: string;
  rating: number | null;
  reviews: number;
  website: string;
  phone: string;
  open_now: boolean | null;
  service_area_only: boolean;
  status: string;
  maps_url: string;
  /** Photos on the listing. Google returns at most ten. */
  photos: number;
  hours_set: boolean;
  open_24h: boolean;
  name_match: boolean;
};

/** "1420 Dundas Street East · Plumber · Open now" — whichever parts Google gave us. */
export function listingMeta(li: Listing): string {
  const parts = [li.service_area_only ? "Serves your area, no shopfront" : li.address, li.category];
  if (li.status === "CLOSED_PERMANENTLY") parts.push("Permanently closed");
  else if (li.status === "CLOSED_TEMPORARILY") parts.push("Temporarily closed");
  else if (li.open_now === true) parts.push("Open now");
  else if (li.open_now === false) parts.push("Closed now");
  return parts.filter(Boolean).join(" · ");
}

/** "4.6 · 87 reviews", or plain words when Google has no rating yet. */
export function listingRating(li: Listing): string {
  if (li.rating === null || li.reviews === 0) return "No reviews yet";
  return `${li.rating} · ${li.reviews} ${li.reviews === 1 ? "review" : "reviews"}`;
}
