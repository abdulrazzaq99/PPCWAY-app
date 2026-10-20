"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ConnectButton } from "@/components/pw/connect-button";
import { counted } from "@/components/pw/first-sync";
import { Chip, PwCard } from "@/components/pw/shell";
import { ago } from "@/lib/when";

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
  const [sync, setSync] = useState<SyncState | null>(null);
  const [reading, setReading] = useState(false);

  // While a pass is running, look again every couple of seconds; when nothing
  // is running, this settles into one request when the screen opens.
  useEffect(() => {
    if (!ads.connected || !ads.customer_id) return;
    let stop = false;
    const look = async () => {
      try {
        const res = await fetch("/api/ads/sync", { cache: "no-store" });
        if (!res.ok || stop) return;
        const now = (await res.json()) as SyncState;
        setSync(now);
        setReading(now.run?.status === "running");
      } catch {
        /* The card still shows what it knew; the next look is seconds away. */
      }
    };
    void look();
    const timer = setInterval(look, reading ? 2000 : 30000);
    return () => {
      stop = true;
      clearInterval(timer);
    };
  }, [ads.connected, ads.customer_id, reading]);

  async function refresh() {
    setReading(true);
    await fetch("/api/ads/sync", { method: "POST" }).catch(() => undefined);
  }

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
          <div className="flex flex-wrap gap-2">
            {ads.customer_id ? (
              <button
                type="button"
                onClick={refresh}
                disabled={reading}
                className="border-pw-border-strong hover:bg-pw-muted rounded-[10px] border px-4 py-2 text-[14px] font-semibold disabled:opacity-60"
              >
                {reading ? "Reading…" : "Refresh now"}
              </button>
            ) : null}
            {canDisconnect ? (
              <button
                type="button"
                onClick={() => setAsking(true)}
                className="border-pw-border-strong hover:bg-pw-muted rounded-[10px] border px-4 py-2 text-[14px] font-semibold"
              >
                Disconnect
              </button>
            ) : null}
          </div>
        ) : (
          <ConnectButton />
        )}
      </div>

      {ads.connected && ads.customer_id ? (
        <p className="text-pw-ink-400 mt-3 text-[13px] leading-[19px]">{lastLook(sync, reading)}</p>
      ) : null}

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

type SyncState = {
  run?: { status: string; stage: string; counts: Record<string, number>; trouble: string } | null;
  last_done_at?: string | null;
  held?: Record<string, number>;
};

/* When we last looked, and what we hold — or why the last look did not work. */
function lastLook(sync: SyncState | null, reading: boolean): string {
  if (reading || sync?.run?.status === "running") {
    return sync?.run?.stage ? `${sync.run.stage}…` : "Reading the account…";
  }
  if (sync?.run?.status === "failed" && sync.run.trouble) {
    return `The last read did not work: ${sync.run.trouble}`;
  }
  if (!sync?.last_done_at) return "Not read yet. The first read happens within fifteen minutes.";
  const held = counted(sync.held ?? {});
  return `Last read ${ago(sync.last_done_at)}${held ? `. We hold ${held}` : ""}.`;
}

function pretty(id: string): string {
  return id.length === 10 ? `${id.slice(0, 3)}-${id.slice(3, 6)}-${id.slice(6)}` : id;
}
