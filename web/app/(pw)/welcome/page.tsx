import type { Metadata } from "next";
import Link from "next/link";
import { AccountPicker } from "@/components/pw/account-picker";
import { ConnectButton } from "@/components/pw/connect-button";
import { Header, PwCard, PwPage } from "@/components/pw/shell";
import { ask } from "@/lib/pw-fetch";

export const metadata: Metadata = { title: "Get started · PPCway" };

type Status = { connected: boolean; customer_id?: string; customer_name?: string };

export default async function WelcomePage() {
  const ads = await ask<Status>("/v1/ads/status", { connected: false });
  const chosen = Boolean(ads.connected && ads.customer_id);

  return (
    <>
      <Header
        eyebrow="Get started"
        title={chosen ? "You are set up" : "Do you already run Google Ads?"}
      />
      <PwPage>
        {chosen ? (
          <PwCard className="p-6 sm:p-8">
            <h2 className="display text-[22px] leading-[28px] font-semibold">
              {ads.customer_name || "Your account"} is connected
            </h2>
            <p className="text-pw-ink-500 mt-2 max-w-[640px] text-[16px] leading-[25px]">
              We read it and nothing more. Your home screen now shows what it spent, what it brought
              back, and where the money went.
            </p>
            <div className="mt-5 flex flex-wrap gap-3">
              <Link
                href="/home"
                className="bg-pw-blue hover:bg-pw-blue-hover rounded-[10px] px-4 py-2 text-[14px] font-semibold text-white"
              >
                Go to your dashboard
              </Link>
              <Link
                href="/campaigns"
                className="border-pw-border-strong hover:bg-pw-muted rounded-[10px] border px-4 py-2 text-[14px] font-semibold"
              >
                See your campaigns
              </Link>
            </div>
          </PwCard>
        ) : (
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <PwCard className="flex flex-col p-6 sm:p-8">
              <p className="text-pw-blue text-[12px] font-bold tracking-[0.08em] uppercase">
                Yes, already advertising
              </p>
              <h2 className="display mt-2 text-[22px] leading-[28px] font-semibold">
                Connect the account you already have
              </h2>
              <p className="text-pw-ink-500 mt-2 text-[16px] leading-[25px]">
                Sign in with Google, choose which account your ads run in, and we read it. We change
                nothing without your yes, and you can disconnect at any time from your own Google
                account.
              </p>
              <div className="mt-5">
                <ConnectButton />
              </div>
            </PwCard>

            <PwCard className="flex flex-col p-6 sm:p-8">
              <p className="text-pw-ink-400 text-[12px] font-bold tracking-[0.08em] uppercase">
                No, new to Google Ads
              </p>
              <h2 className="display mt-2 text-[22px] leading-[28px] font-semibold">
                Start from nothing
              </h2>
              <p className="text-pw-ink-500 mt-2 text-[16px] leading-[25px]">
                This path creates an account for you under PPCway and walks you through a first
                campaign in about fifteen minutes. It is not switched on yet: it needs a PPCway
                manager account and Google&rsquo;s approval to create accounts on your behalf.
              </p>
              <p className="text-pw-ink-500 mt-3 text-[16px] leading-[25px]">
                In the meantime, the free audit tells you what a campaign would be worth in your
                town before you spend anything.
              </p>
              <div className="mt-5">
                <Link
                  href="/audit"
                  className="border-pw-border-strong hover:bg-pw-muted inline-block rounded-[10px] border px-4 py-2 text-[14px] font-semibold"
                >
                  Run the free audit
                </Link>
              </div>
            </PwCard>
          </div>
        )}

        {ads.connected && !ads.customer_id ? <AccountPicker /> : null}
      </PwPage>
    </>
  );
}
