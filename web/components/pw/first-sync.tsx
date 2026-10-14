"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

/*
  The import, while it happens.

  Connecting an account used to jump straight to "you are set up", which was a
  small lie: nothing had been read yet, and the dashboard behind it was empty
  until somebody opened a screen that asked Google. Now the first sync is a
  thing you watch — the campaigns, the keywords, the ads, then ninety days of
  history — and the counts are the account's own, as they arrive.

  It polls rather than streams. A stream would be prettier; a poll survives a
  dropped connection, a cold start and a phone going to sleep, which this has to.
*/
type Run = {
  id: string;
  kind: string;
  status: "running" | "done" | "failed";
  stage: string;
  counts: Record<string, number>;
  trouble: string;
};

type State = {
  connected: boolean;
  customer_name?: string;
  run?: Run | null;
  last_done_at?: string | null;
  held?: { campaigns?: number; days?: number };
};

const THINGS: [string, string, string][] = [
  ["campaigns", "campaign", "campaigns"],
  ["ad_groups", "ad group", "ad groups"],
  ["keywords", "keyword", "keywords"],
  ["ads", "ad", "ads"],
  ["days", "day of history", "days of history"],
];

export function counted(counts: Record<string, number>): string {
  const parts = THINGS.filter(([key]) => counts[key] > 0).map(([key, one, many]) =>
    counts[key] === 1 ? `1 ${one}` : `${counts[key].toLocaleString()} ${many}`,
  );
  if (parts.length === 0) return "";
  if (parts.length === 1) return parts[0];
  return `${parts.slice(0, -1).join(", ")} and ${parts[parts.length - 1]}`;
}

export function FirstSync({ onDone }: { onDone?: () => void }) {
  const router = useRouter();
  const [state, setState] = useState<State | null>(null);
  const [trouble, setTrouble] = useState("");
  const started = useRef(false);

  useEffect(() => {
    let stop = false;

    async function look() {
      try {
        const res = await fetch("/api/ads/sync", { cache: "no-store" });
        if (!res.ok) return;
        const now = (await res.json()) as State;
        if (stop) return;
        setState(now);
        // Nothing has ever been read, and nothing is reading: start one.
        if (!started.current && !now.run && now.connected) {
          started.current = true;
          const made = await fetch("/api/ads/sync", { method: "POST" });
          if (!made.ok) {
            const said = (await made.json().catch(() => ({}))) as { error?: string };
            if (!stop) setTrouble(said.error ?? "We could not start reading the account.");
          }
          return;
        }
        if (now.run?.status === "done") {
          stop = true;
          onDone?.();
          router.refresh();
        }
      } catch {
        /* A missed poll is not news; the next one is a second and a half away. */
      }
    }

    void look();
    const timer = setInterval(look, 1500);
    return () => {
      stop = true;
      clearInterval(timer);
    };
  }, [router, onDone]);

  const run = state?.run ?? null;
  const counts = run?.counts ?? {};
  const found = counted(counts);

  if (trouble || run?.status === "failed") {
    return (
      <div className="bg-pw-bad-bg rounded-[14px] p-4">
        <p className="text-[15px] leading-[23px] font-semibold">
          We could not finish reading the account.
        </p>
        <p className="text-pw-bad-ink mt-1 text-[14px] leading-[21px]">{trouble || run?.trouble}</p>
      </div>
    );
  }

  return (
    <div className="bg-pw-blue-tint-2 rounded-[14px] p-4">
      <div className="flex items-center gap-3">
        <span
          className="border-pw-blue inline-block size-4 animate-spin rounded-full border-2 border-r-transparent"
          aria-hidden
        />
        <p className="text-[15px] leading-[23px] font-semibold">
          {run?.stage || "Asking Google for your account"}
        </p>
      </div>
      <p className="text-pw-ink-600 mt-2 text-[14px] leading-[21px]">
        {found
          ? `So far: ${found}.`
          : "This takes about half a minute. You can leave this page; it carries on without you."}
      </p>
    </div>
  );
}
