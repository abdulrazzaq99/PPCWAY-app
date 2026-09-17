import type { Metadata } from "next";
import { AuditReportSample } from "@/components/audit/report-views";
import { AUDIT_REPORT_VIEWS } from "@/components/audit/view-names";
import { pickView } from "@/lib/view-param";

export const metadata: Metadata = { title: "Your audit: PPCWay" };

export default async function AuditReportSamplePage({
  searchParams,
}: {
  searchParams: Promise<{ view?: string }>;
}) {
  const { view } = await searchParams;
  return <AuditReportSample view={pickView(AUDIT_REPORT_VIEWS, view)} />;
}
