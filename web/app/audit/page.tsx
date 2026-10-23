import type { Metadata } from "next";
import { FreeAudit } from "@/components/audit/funnel/free-audit";
import {
  AuditFooter,
  AuditHeader,
  Closing,
  Promises,
  Questions,
  WhatWeCheck,
} from "@/components/audit/funnel/parts";

export const metadata: Metadata = {
  title: "Free Google Ads audit · PPCway",
  description:
    "Tell us your business and website. We check your site, tracking and search presence, then show your score and the issues worth fixing first. Free, no card, no account.",
};

/*
  The free audit, in the client's Version D flow: one page, one state machine,
  switching layout at 640px. It is the whole of what a stranger can reach, and
  it asks for nothing until it has something to show for it.
*/
export default function AuditPage() {
  return (
    <div className="site min-h-dvh bg-[#F6F5F2] text-[#15112A]">
      <AuditHeader />
      <FreeAudit />
      <WhatWeCheck />
      <Promises />
      <Questions />
      <Closing />
      <AuditFooter />
    </div>
  );
}
