import Link from "next/link";
import type { ReactNode } from "react";
import { ConnectButton } from "@/components/pw/connect-button";
import { PwCard } from "@/components/pw/shell";

/*
  The two screens-worth of honesty this app needs while the rest is built.

  A screen whose machinery does not exist says what it will do and who it is
  waiting for. It never shows the prototype's sample numbers: those belong to a
  plumber in Toronto who does not exist, and a real business reading them would
  be making decisions on fiction.
*/
export function NotConnected({ what }: { what: string }) {
  return (
    <PwCard className="p-6 sm:p-8">
      <h2 className="display text-[22px] leading-[28px] font-semibold">
        Connect your Google Ads account
      </h2>
      <p className="text-pw-ink-500 mt-2 max-w-[620px] text-[16px] leading-[25px]">
        {what} We read it; we change nothing without your yes, and you can disconnect whenever you
        like.
      </p>
      <div className="mt-5">
        <ConnectButton />
      </div>
    </PwCard>
  );
}

export function NotBuilt({
  title,
  children,
  needs,
}: {
  title: string;
  children: ReactNode;
  needs?: string;
}) {
  return (
    <PwCard className="p-6 sm:p-8">
      <h2 className="display text-[22px] leading-[28px] font-semibold">{title}</h2>
      <div className="text-pw-ink-500 mt-3 flex max-w-[680px] flex-col gap-3 text-[16px] leading-[25px]">
        {children}
      </div>
      {needs ? (
        <p className="border-pw-divider text-pw-ink-400 mt-5 border-t pt-4 text-[14px] leading-[21px]">
          {needs}
        </p>
      ) : null}
      <div className="mt-5 flex flex-wrap gap-3">
        <Link
          href="/home"
          className="border-pw-border-strong hover:bg-pw-muted rounded-[10px] border px-4 py-2 text-[14px] font-semibold"
        >
          Back to home
        </Link>
        <Link
          href="/tools/audit"
          className="bg-pw-blue hover:bg-pw-blue-hover rounded-[10px] px-4 py-2 text-[14px] font-semibold text-white"
        >
          See your website audit
        </Link>
      </div>
    </PwCard>
  );
}
