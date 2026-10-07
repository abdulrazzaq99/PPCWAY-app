import type { Metadata } from "next";
import { MyAudits } from "@/components/audit/my-audits";

export const metadata: Metadata = { title: "Your audits: PPCWay" };

export default function MyAuditsPage() {
  return <MyAudits />;
}
