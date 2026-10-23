import type { Metadata } from "next";
import Link from "next/link";
import { FreeAudit } from "@/components/audit/funnel/free-audit";
import { AuditFooter, AuditHeader } from "@/components/audit/funnel/parts";
import type { Unlocked } from "@/lib/funnel";

export const metadata: Metadata = { title: "Your audit · PPCway" };

const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8300";

/*
  The link in the email. It opens the report on whatever device reads the
  email, which is rarely the one that asked for it.

  Read here on the server rather than in the browser: the page then arrives
  with the report already in it, and a link that no longer opens anything says
  so plainly instead of flashing an empty report first.
*/
async function opened(token: string): Promise<Unlocked | null> {
  try {
    const res = await fetch(`${BACKEND}/v1/public/audits/open/${encodeURIComponent(token)}`, {
      cache: "no-store",
    });
    if (!res.ok) return null;
    return (await res.json()) as Unlocked;
  } catch {
    return null;
  }
}

export default async function OpenAuditPage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = await params;
  const report = await opened(token);

  if (!report) {
    return (
      <div className="site min-h-dvh bg-[#F6F5F2] text-[#15112A]">
        <AuditHeader />
        <main className="mx-auto max-w-[620px] px-6 py-20">
          <h1 className="display text-[28px] leading-[1.15] font-semibold">
            That link does not open anything.
          </h1>
          <p className="mt-4 text-[16px] leading-[1.6] text-[#4A4560]">
            It may have expired, or been replaced by a newer one. Running the audit again takes
            about a minute.
          </p>
          <Link
            href="/audit"
            className="tap mt-6 inline-flex h-[54px] items-center rounded-[14px] bg-[#2F5BEA] px-7 text-[17px] font-semibold text-white"
          >
            Run my free audit
          </Link>
        </main>
        <AuditFooter />
      </div>
    );
  }

  return (
    <div className="site min-h-dvh bg-[#F6F5F2] text-[#15112A]">
      <AuditHeader />
      <FreeAudit opened={report} />
      <AuditFooter />
    </div>
  );
}
