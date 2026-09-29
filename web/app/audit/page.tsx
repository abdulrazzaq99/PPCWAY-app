import type { Metadata } from "next";
import { AuditFindView } from "@/components/audit/find-views";
import { AUDIT_VIEWS } from "@/components/audit/view-names";
import { readListing, searchListings } from "@/lib/listings";
import { pickView } from "@/lib/view-param";

export const metadata: Metadata = {
  title: "Free audit: PPCWay",
  description:
    "We check your Google listing, your website and whether your ads are showing, then tell you what to fix first.",
};

/*
  With a name typed, the matches and the chosen listing come from Google through the
  backend. Without one, the drawn states still answer ?view= so the Figma frames can
  be reviewed.
*/
export default async function AuditPage({
  searchParams,
}: {
  searchParams: Promise<{
    view?: string;
    name?: string;
    city?: string;
    site?: string;
    place?: string;
  }>;
}) {
  const { view, name, city, site, place } = await searchParams;
  const chosenView = pickView(AUDIT_VIEWS, view);
  const typed = {
    ...(name ? { name } : {}),
    ...(city ? { city } : {}),
    ...(site ? { site: site.trim().replace(/^https?:\/\//, "") } : {}),
  };

  if (chosenView === "results" && name && name.trim().length > 1) {
    const { listings, error } = await searchListings(name.trim(), (city ?? "").trim());
    return <AuditFindView view="results" typed={typed} listings={listings} error={error} />;
  }
  if (chosenView === "confirm" && place) {
    const listing = await readListing(place);
    if (listing) return <AuditFindView view="confirm" typed={typed} chosen={listing} />;
    return <AuditFindView view="not-found" typed={typed} />;
  }
  return <AuditFindView view={chosenView} typed={typed} />;
}
