import Image from "next/image";
import type { Metadata } from "next";
import { Report } from "@/components/pw/report";
import { askPublic } from "@/lib/public-fetch";
import type { ReportSaid } from "@/lib/reports";

export const metadata: Metadata = { title: "A PPCway report", robots: { index: false } };

/*
  A report read by somebody with no account: an accountant, a partner, a
  landlord asking what the advertising costs. They see the figures and the words
  that explain them, and nothing else — no people, no other accounts, no way in.

  The page says whose report it is and when the link dies, because a document
  with no date on it is the one that gets quoted back wrongly in a year.
*/
export default async function SharedReportPage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = await params;
  const said = await askPublic<ReportSaid>(`/v1/public/report/${encodeURIComponent(token)}`);

  if (!said || !said.read) {
    return (
      <main className="bg-pw-ground min-h-screen px-5 py-16">
        <div className="bg-pw-card border-pw-border mx-auto max-w-[560px] rounded-[18px] border p-7">
          <h1 className="display text-[22px] leading-[28px] font-semibold">
            This link has expired
          </h1>
          <p className="text-pw-ink-500 mt-3 text-[15px] leading-[23px]">
            A shared PPCway report works for a fortnight, and can be stopped sooner by whoever
            shared it. Ask them for a new one.
          </p>
        </div>
      </main>
    );
  }

  return (
    <main className="bg-pw-ground min-h-screen">
      <header className="border-pw-border bg-pw-card border-b px-5 py-5 sm:px-8">
        <div className="mx-auto flex max-w-[1180px] flex-wrap items-center justify-between gap-4">
          <div className="min-w-0">
            <p className="text-pw-ink-400 text-[13px]">
              Google Ads report · {said.starts_on} to {said.ends_on}
            </p>
            <h1 className="display text-[24px] leading-[30px] font-semibold">
              {said.business || "Google Ads report"}
            </h1>
          </div>
          <Image
            src="/brand/ppcway-logo.svg"
            alt="PPCway"
            width={116}
            height={28}
            className="h-[26px] w-auto"
          />
        </div>
      </header>
      <div className="mx-auto flex max-w-[1180px] flex-col gap-4 px-5 py-6 sm:px-8">
        <Report said={said} />
        <p className="text-pw-ink-400 text-[13px] leading-[19px]">
          This is a read-only copy, shared by {said.business || "the advertiser"}. The link stops
          working{" "}
          {said.expires_at
            ? `on ${new Date(said.expires_at).toLocaleDateString()}`
            : "when it expires"}
          . Nothing here can be changed from this page.
        </p>
      </div>
    </main>
  );
}
