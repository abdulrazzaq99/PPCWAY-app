import type { Metadata } from "next";
import { LiveReport } from "@/components/audit/live-report";

export const metadata: Metadata = { title: "Your website check: PPCWay" };

export default async function AuditReportPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ paper?: string }>;
}) {
  const { id } = await params;
  // `?paper=1` is how the PDF printer asks for this page without the furniture.
  const { paper } = await searchParams;
  return <LiveReport id={id} paper={paper === "1"} />;
}
