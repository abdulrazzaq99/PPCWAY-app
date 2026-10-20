import Image from "next/image";
import type { Metadata } from "next";
import { askPublic } from "@/lib/public-fetch";

export const metadata: Metadata = { title: "Website fix list", robots: { index: false } };

/*
  The fix list, for whoever looks after the website. They have no PPCway account
  and did not ask for this, so the page opens by saying what it is and who sent
  it, and every item says what was found, which pages it affects and what a fix
  looks like.

  No sign-in, no account to make, nothing to buy. A developer who thinks they
  have been sent a marketing funnel will close the tab.
*/
type Job = { title: string; summary: string; detail: string[]; fix: string };
type Fine = { title: string; summary: string };
type Said = {
  site: string;
  checked_at: string | null;
  score: number | null;
  expires_at: string;
  jobs: Job[];
  fine: Fine[];
};

export default async function FixListPage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = await params;
  const said = await askPublic<Said>(`/v1/public/fixes/${encodeURIComponent(token)}`);

  if (!said) {
    return (
      <main className="bg-pw-ground min-h-screen px-5 py-16">
        <div className="bg-pw-card border-pw-border mx-auto max-w-[560px] rounded-[18px] border p-7">
          <h1 className="display text-[22px] leading-[28px] font-semibold">
            This link has expired
          </h1>
          <p className="text-pw-ink-500 mt-3 text-[15px] leading-[23px]">
            A shared fix list works for a fortnight. Ask whoever sent it for a new one.
          </p>
        </div>
      </main>
    );
  }

  const site = said.site.replace(/^https?:\/\//, "").replace(/\/$/, "");

  return (
    <main className="bg-pw-ground min-h-screen">
      <header className="border-pw-border bg-pw-card border-b px-5 py-5 sm:px-8">
        <div className="mx-auto flex max-w-[860px] flex-wrap items-center justify-between gap-4">
          <div className="min-w-0">
            <p className="text-pw-ink-400 text-[13px]">Website fix list</p>
            <h1 className="display text-[24px] leading-[30px] font-semibold">{site}</h1>
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

      <div className="mx-auto flex max-w-[860px] flex-col gap-4 px-5 py-6 sm:px-8">
        <div className="bg-pw-card border-pw-border rounded-[18px] border p-5 sm:p-6">
          <p className="text-[16px] leading-[25px]">
            {said.jobs.length === 0 ? (
              <>
                Nothing on <strong className="font-semibold">{site}</strong> needs fixing for Google
                Ads. {said.fine.length} checks passed.
              </>
            ) : (
              <>
                <strong className="font-semibold">
                  {said.jobs.length} {said.jobs.length === 1 ? "thing" : "things"} on {site} are
                  costing this business money in Google Ads.
                </strong>{" "}
                Each one below says what was found and what a fix looks like. There is nothing to
                sign into and no account to make.
              </>
            )}
          </p>
          <p className="text-pw-ink-400 mt-3 text-[13px]">
            {said.checked_at ? `Checked ${new Date(said.checked_at).toLocaleDateString()}` : ""}
            {said.score !== null ? ` · ${said.score} out of 100` : ""}
          </p>
        </div>

        {said.jobs.map((job, i) => (
          <div
            key={job.title}
            className="bg-pw-card border-pw-border rounded-[18px] border p-5 sm:p-6"
          >
            <h2 className="flex items-baseline gap-2 text-[17px] leading-[23px] font-semibold">
              <span className="text-pw-ink-400 pw-num text-[14px]">{i + 1}</span>
              {job.title}
            </h2>
            <p className="mt-2 text-[15px] leading-[24px]">{job.summary}</p>
            {job.detail.length ? (
              <ul className="text-pw-ink-600 mt-3 flex list-disc flex-col gap-1 pl-5 text-[14px] leading-[21px]">
                {job.detail.map((line) => (
                  <li key={line}>{line}</li>
                ))}
              </ul>
            ) : null}
            {job.fix ? (
              <div className="bg-pw-blue-tint-2 mt-4 rounded-[12px] p-4">
                <p className="text-[14px] leading-[22px]">
                  <strong className="font-semibold">What to do:</strong> {job.fix}
                </p>
              </div>
            ) : null}
          </div>
        ))}

        {said.fine.length ? (
          <div className="bg-pw-card border-pw-border rounded-[18px] border p-5 sm:p-6">
            <h2 className="text-[15px] font-semibold">Already fine</h2>
            <p className="text-pw-ink-500 mt-2 text-[14px] leading-[21px]">
              {said.fine.map((f) => f.title).join(" · ")}
            </p>
          </div>
        ) : null}

        <p className="text-pw-ink-400 text-[13px] leading-[19px]">
          This list was shared from PPCway and stops working on{" "}
          {new Date(said.expires_at).toLocaleDateString()}. It is a read-only page: nothing here
          changes the website or the advertising.
        </p>
      </div>
    </main>
  );
}
