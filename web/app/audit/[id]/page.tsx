import type { Metadata } from "next";
import { AuditReportView } from "@/components/landing/audit-report";

export const metadata: Metadata = { title: "Your website check: PPCWay" };

export default async function AuditReportPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <AuditReportView id={id} />;
}
