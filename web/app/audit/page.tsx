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
  searchParams: Promise<{ view?: string }>;
}) {
  const { view } = await searchParams;
  return <AuditFindView view={pickView(AUDIT_VIEWS, view)} />;
}
