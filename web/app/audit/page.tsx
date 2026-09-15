import type { Metadata } from "next";
import { AuditRequest } from "@/components/landing/audit-request";

export const metadata: Metadata = {
  title: "Get a free audit: PPCWay",
  description:
    "A free check of your website, the same eight checks an agency runs before spending a dollar.",
};

export default function AuditPage() {
  return <AuditRequest />;
}
