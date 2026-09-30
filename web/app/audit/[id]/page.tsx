import type { Metadata } from "next";
import { LiveReport } from "@/components/audit/live-report";

export const metadata: Metadata = { title: "Your website check: PPCWay" };

export default async function AuditReportPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <LiveReport id={id} />;
}
