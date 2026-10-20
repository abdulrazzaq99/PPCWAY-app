"use client";

import { useState } from "react";
import { Chip } from "@/components/pw/shell";
import type { Share } from "@/lib/reports";

/*
  "Send this to my accountant." A link that needs no login, dies in a fortnight,
  and can be stopped before then.

  The link is shown rather than only copied, because somebody who cannot see
  what they are about to send does not know whether to send it.
*/
export function ShareReport({ shares }: { shares: Share[] }) {
  const [made, setMade] = useState("");
  const [expires, setExpires] = useState("");
  const [busy, setBusy] = useState(false);
  const [trouble, setTrouble] = useState("");
  const [live, setLive] = useState(shares);
  const [copied, setCopied] = useState(false);

  async function make() {
    setBusy(true);
    setTrouble("");
    try {
      const res = await fetch("/api/reports/share", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ days: 14 }),
      });
      const said = (await res.json().catch(() => ({}))) as {
        url?: string;
        expires_at?: string;
        id?: string;
        error?: string;
      };
      if (!res.ok || !said.url) {
        setTrouble(said.error ?? "That link could not be made.");
        return;
      }
      setMade(said.url);
      setExpires(said.expires_at ?? "");
      setLive([
        ...live,
        {
          id: said.id ?? "",
          expires_at: said.expires_at ?? "",
          opened: 0,
          sent_to: "",
        },
      ]);
    } catch {
      setTrouble("We could not reach the service.");
    } finally {
      setBusy(false);
    }
  }

  async function stop(id: string) {
    await fetch(`/api/reports/share?id=${encodeURIComponent(id)}`, { method: "DELETE" });
    setLive(live.filter((l) => l.id !== id));
    setMade("");
  }

  async function copy() {
    try {
      await navigator.clipboard.writeText(made);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  }

  return (
    <div className="flex min-w-[260px] flex-col items-start gap-2">
      <button
        type="button"
        onClick={make}
        disabled={busy}
        className="bg-pw-blue hover:bg-pw-blue-hover h-[40px] rounded-[10px] px-4 text-[14px] font-semibold text-white disabled:opacity-60"
      >
        {busy ? "Making a link…" : "Share this report"}
      </button>

      {trouble ? (
        <p className="text-pw-bad text-[13px]" role="alert">
          {trouble}
        </p>
      ) : null}

      {made ? (
        <div className="border-pw-blue-tint bg-pw-blue-tint w-full rounded-[12px] border p-3">
          <p className="text-pw-blue-ink text-[13px] leading-[19px] font-semibold">
            Anybody with this link can read this report until{" "}
            {expires ? new Date(expires).toLocaleDateString() : "it expires"}. They cannot sign in,
            change anything, or see anything else.
          </p>
          <p className="text-pw-ink-700 mt-2 text-[12px] break-all">{made}</p>
          <button
            type="button"
            onClick={copy}
            className="text-pw-blue mt-2 text-[13px] font-semibold"
          >
            {copied ? "Copied" : "Copy the link"}
          </button>
        </div>
      ) : null}

      {live.length ? (
        <ul className="flex w-full flex-col gap-1">
          {live.map((link) => (
            <li key={link.id} className="flex flex-wrap items-center gap-2 text-[12px]">
              <Chip tone="neutral">
                {link.opened === 0
                  ? "Not opened yet"
                  : `Opened ${link.opened} ${link.opened === 1 ? "time" : "times"}`}
              </Chip>
              <span className="text-pw-ink-400">
                until {new Date(link.expires_at).toLocaleDateString()}
              </span>
              <button
                type="button"
                onClick={() => void stop(link.id)}
                className="text-pw-bad font-semibold"
              >
                Stop it working
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
