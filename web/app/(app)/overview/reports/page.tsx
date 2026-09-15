import { ReportView } from "@/components/app/overview-views";
import { REPORT_VIEWS } from "@/components/app/view-names";
import { pickView } from "@/lib/view-param";

export default async function ReportsPage({
  searchParams,
}: {
  searchParams: Promise<{ view?: string }>;
}) {
  const { view } = await searchParams;
  return <ReportView view={pickView(REPORT_VIEWS, view)} />;
}
