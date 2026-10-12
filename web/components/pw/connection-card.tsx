"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { ConnectButton } from "@/components/pw/connect-button";
import { Chip, PwCard } from "@/components/pw/shell";

/*
  The Google Ads connection, and the way out of it. Disconnecting tells Google
  the permission is over and destroys the stored key here; the record that a
  connection existed stays, because the history should not develop holes.
*/
export function ConnectionCard({
  ads,
  canDisconnect,
}: {
  ads: { connected: boolean; customer_id?: string; customer_name?: string };
  canDisconnect: boolean;
}) {
  const router = useRouter();
  const [asking, setAsking] = useState(false);
  const [busy, setBusy] = useState(false);

  async function disconnect() {
    setBusy(true);
    try {
      await fetch("/api/ads/disconnect", { method: "POST" });
      setAsking(false);
      router.refresh();
    } finally {
      setBusy(false);
    }
  }

  return (
    <PwCard className="p-5 sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <h2 className="flex flex-wrap items-center gap-2 text-[17px] leading-[22px] font-semibold">
            Google Ads
            {ads.connected ? (
              <Chip tone="good">Connected</Chip>
            ) : (
              <Chip tone="neutral">Not connected</Chip>
            )}
          </h2>
          <p className="text-pw-ink-500 mt-1 text-[14px] leading-[21px]">
            {ads.connected
              ? ads.customer_id
                ? `We read ${ads.customer_name || "account"} ${pretty(ads.customer_id)}. We change nothing without your yes.`
                : "Connected, but no account chosen yet."
              : "Connect your account, read only, and the dashboard fills with your own numbers."}
          </p>
        </div>
        {ads.connected ? (
          canDisconnect ? (
            <button
              type="button"
              onClick={() => setAsking(true)}
              className="border-pw-border-strong hover:bg-pw-muted rounded-[10px] border px-4 py-2 text-[14px] font-semibold"
            >
              Disconnect
            </button>
          ) : null
        ) : (
          <ConnectButton />
        )}
      </div>

      {asking ? (
        <div className="border-pw-warn-border bg-pw-warn-bg mt-4 rounded-[12px] border p-4">
          <p className="text-pw-warn-ink text-[15px] leading-[22px]">
            <strong className="font-bold">Disconnect Google Ads?</strong> We stop reading your
            account immediately and destroy the stored permission. Your campaigns are untouched, and
            you can connect again whenever you like.
          </p>
          <div className="mt-3 flex flex-wrap gap-3">
            <button
              type="button"
              onClick={disconnect}
              disabled={busy}
              className="bg-pw-warn-ink rounded-[10px] px-4 py-2 text-[14px] font-semibold text-white disabled:opacity-70"
            >
              {busy ? "Disconnecting…" : "Yes, disconnect"}
            </button>
            <button
              type="button"
              onClick={() => setAsking(false)}
              className="border-pw-border-strong rounded-[10px] border px-4 py-2 text-[14px] font-semibold"
            >
              Keep it connected
            </button>
          </div>
        </div>
      ) : null}
    </PwCard>
  );
}

function pretty(id: string): string {
  return id.length === 10 ? `${id.slice(0, 3)}-${id.slice(3, 6)}-${id.slice(6)}` : id;
}
