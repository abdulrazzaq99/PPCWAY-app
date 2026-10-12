"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

/*
  Who is signed in, and the two ways out. "Everywhere" is the one that matters
  after a lost laptop, and it is the only honest answer to "am I still signed in
  somewhere else?".
*/
export function AccountCard({ business, plan }: { business: string; plan?: string }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState("");

  async function leave(where: "here" | "everywhere") {
    setBusy(where);
    try {
      await fetch(where === "here" ? "/api/auth/signout" : "/api/auth/signout-everywhere", {
        method: "POST",
      });
      router.push("/login");
      router.refresh();
    } finally {
      setBusy("");
    }
  }

  return (
    <div className="border-pw-border rounded-[14px] border">
      <button
        type="button"
        onClick={() => setOpen((was) => !was)}
        aria-expanded={open}
        className="hover:bg-pw-muted flex w-full items-center gap-3 rounded-[14px] p-3 text-left"
      >
        <span className="bg-pw-muted text-pw-ink-700 flex size-9 shrink-0 items-center justify-center rounded-[10px] text-[12px] font-bold">
          {initials(business)}
        </span>
        <span className="min-w-0 flex-1">
          <span className="block truncate text-[14px] leading-[18px] font-semibold">
            {business}
          </span>
          {plan ? (
            <span className="text-pw-ink-500 block truncate text-[12px] leading-[16px]">
              {plan}
            </span>
          ) : null}
        </span>
        <span aria-hidden className="text-pw-ink-400 text-[12px]">
          {open ? "▴" : "▾"}
        </span>
      </button>

      {open ? (
        <div className="border-pw-divider flex flex-col border-t p-2">
          <button
            type="button"
            onClick={() => void leave("here")}
            disabled={Boolean(busy)}
            className="hover:bg-pw-muted rounded-[8px] px-3 py-2 text-left text-[14px] disabled:opacity-60"
          >
            {busy === "here" ? "Signing out…" : "Sign out"}
          </button>
          <button
            type="button"
            onClick={() => void leave("everywhere")}
            disabled={Boolean(busy)}
            className="text-pw-bad hover:bg-pw-muted rounded-[8px] px-3 py-2 text-left text-[14px] disabled:opacity-60"
          >
            {busy === "everywhere" ? "Ending every session…" : "Sign out everywhere"}
          </button>
          <p className="text-pw-ink-400 px-3 pt-1 pb-1 text-[12px] leading-[17px]">
            Everywhere ends every browser and phone you are signed in on.
          </p>
        </div>
      ) : null}
    </div>
  );
}

function initials(name: string): string {
  return (
    name
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((w) => w[0]?.toUpperCase() ?? "")
      .join("") || "PW"
  );
}
