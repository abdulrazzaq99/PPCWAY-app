"use client";

import { useState } from "react";

/*
  One button, one job: start the trip to Google. It is a client component only
  because the answer is a URL we have to follow, and the server cannot follow it
  for us.
*/
export function ConnectButton({
  label = "Connect Google Ads",
  className,
}: {
  label?: string;
  className?: string;
}) {
  const [going, setGoing] = useState(false);
  const [trouble, setTrouble] = useState("");

  async function go() {
    setGoing(true);
    setTrouble("");
    try {
      const res = await fetch("/api/ads/connect", { method: "POST" });
      const said = (await res.json().catch(() => ({}))) as { url?: string; error?: string };
      if (res.ok && said.url) {
        window.location.href = said.url;
        return;
      }
      setTrouble(said.error ?? "Connecting Google Ads is not available right now.");
    } catch {
      setTrouble("We could not reach the service. Try again in a minute.");
    } finally {
      setGoing(false);
    }
  }

  return (
    <span className="inline-flex flex-col items-start gap-1">
      <button
        type="button"
        onClick={go}
        disabled={going}
        className={
          className ??
          "bg-pw-blue hover:bg-pw-blue-hover rounded-[10px] px-4 py-2 text-[14px] font-semibold text-white disabled:opacity-70"
        }
      >
        {going ? "Opening Google…" : label}
      </button>
      {trouble ? (
        <span role="alert" className="text-pw-bad text-[13px]">
          {trouble}
        </span>
      ) : null}
    </span>
  );
}
