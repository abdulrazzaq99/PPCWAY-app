import type { Metadata } from "next";
import { AuditFindView } from "@/components/audit/find-views";
import { AUDIT_VIEWS } from "@/components/audit/view-names";
import { pickView } from "@/lib/view-param";

export const metadata: Metadata = {
  title: "Free audit: PPCWay",
  description:
    "We check your Google listing, your website and whether your ads are showing, then tell you what to fix first.",
};

export default async function AuditPage({
  searchParams,
}: {
  searchParams: Promise<{ view?: string; name?: string; city?: string; site?: string }>;
}) {
  const { view, name, city, site } = await searchParams;
  const typed = {
    ...(name ? { name } : {}),
    ...(city ? { city } : {}),
    ...(site ? { site: site.trim().replace(/^https?:\/\//, "") } : {}),
  };
  return <AuditFindView view={pickView(AUDIT_VIEWS, view)} typed={typed} />;
}
