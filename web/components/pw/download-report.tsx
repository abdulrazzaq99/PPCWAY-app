"use client";

import { DownloadSimpleIcon } from "@phosphor-icons/react";
import { useState } from "react";

/*
  "Download PDF". The PDF is printed when it is asked for, from the same figures
  this page shows, so it takes a few seconds: the button says it is working
  rather than looking dead, and says so plainly if the printing fails.
*/
export function DownloadReport({ days }: { days: number }) {
  const [busy, setBusy] = useState(false);
  const [trouble, setTrouble] = useState("");

  async function download() {
    setBusy(true);
    setTrouble("");
    try {
      const res = await fetch(`/api/reports/pdf?days=${days}`);
      if (!res.ok) {
        const said = (await res.json().catch(() => ({}))) as { error?: string };
        setTrouble(said.error ?? "The PDF could not be made just now. Try again in a minute.");
        return;
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = fileName(res.headers.get("content-disposition")) ?? "PPCWay report.pdf";
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 10_000);
    } catch {
      setTrouble("We could not reach the service. Try again in a minute.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col items-end gap-1.5">
      <button
        type="button"
        onClick={download}
        disabled={busy}
        aria-busy={busy}
        className="bg-pw-blue hover:bg-pw-blue-hover flex h-[42px] items-center gap-2 rounded-[12px] px-4 text-[15px] font-semibold whitespace-nowrap text-white transition-transform active:scale-[0.98] disabled:opacity-75 motion-reduce:transition-none"
      >
        <DownloadSimpleIcon size={18} weight="bold" className={busy ? "animate-pulse" : ""} />
        {busy ? "Preparing the PDF…" : "Download PDF"}
      </button>
      {trouble ? (
        <p role="alert" className="text-pw-bad max-w-[320px] text-right text-[13px] leading-[18px]">
          {trouble}
        </p>
      ) : null}
    </div>
  );
}

/** The name the server gave the file, preferring its UTF-8 spelling. */
function fileName(disposition: string | null): string | null {
  if (!disposition) return null;
  const utf8 = /filename\*=UTF-8''([^;]+)/i.exec(disposition);
  if (utf8) {
    try {
      return decodeURIComponent(utf8[1]);
    } catch {
      // Fall through to the plain name.
    }
  }
  const plain = /filename="([^"]+)"/i.exec(disposition);
  return plain ? plain[1] : null;
}
