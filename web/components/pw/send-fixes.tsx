"use client";

import { useState } from "react";

/*
  "Send the fix list to my web person."

  The person who has to do the work almost never has a PPCway account, so what
  they get is a link that needs no login and dies in a fortnight. The form says
  that before it asks for an address, because somebody about to send their
  developer a marketing login would rather not.
*/
export function SendFixes({ runId, jobs }: { runId: string; jobs: number }) {
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [link, setLink] = useState("");
  const [sent, setSent] = useState(false);
  const [trouble, setTrouble] = useState("");

  async function send() {
    setBusy(true);
    setTrouble("");
    try {
      const res = await fetch(`/api/audit/${encodeURIComponent(runId)}/share`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ email: email.trim() || null, days: 14 }),
      });
      const said = (await res.json().catch(() => ({}))) as {
        url?: string;
        emailed?: boolean;
        error?: string;
      };
      if (!res.ok || !said.url) {
        setTrouble(said.error ?? "That could not be sent.");
        return;
      }
      setLink(said.url);
      setSent(Boolean(said.emailed));
    } catch {
      setTrouble("We could not reach the service.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <div>
        <h2 className="text-[17px] leading-[22px] font-semibold">
          Send the fix list to your web person
        </h2>
        <p className="text-pw-ink-500 mt-1 max-w-[620px] text-[14px] leading-[21px]">
          They get a page with {jobs === 0 ? "the findings" : `the ${jobs} findings`}, what each one
          means and what a fix looks like. No account, no sign-in, and the link stops working in a
          fortnight.
        </p>
      </div>

      <div className="flex flex-wrap items-end gap-3">
        <label className="flex min-w-[240px] flex-1 flex-col gap-[6px]">
          <span className="text-[14px] font-semibold">Their email</span>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="dev@theirwebshop.ca"
            className="border-pw-border-input bg-pw-card h-[44px] rounded-[12px] border px-3 text-[15px]"
          />
        </label>
        <button
          type="button"
          onClick={send}
          disabled={busy}
          className="bg-pw-blue hover:bg-pw-blue-hover h-[44px] rounded-[12px] px-4 text-[15px] font-semibold text-white disabled:opacity-60"
        >
          {busy ? "Sending…" : email.trim() ? "Send it" : "Just give me the link"}
        </button>
      </div>

      {trouble ? (
        <p className="text-pw-bad text-[14px]" role="alert">
          {trouble}
        </p>
      ) : null}

      {link ? (
        <div className="border-pw-blue-tint bg-pw-blue-tint rounded-[12px] border p-4">
          <p className="text-pw-blue-ink text-[14px] leading-[21px] font-semibold">
            {sent
              ? "Sent. They can open it without an account, and it works for a fortnight."
              : "Here is the link. Anybody who has it can read the fix list for a fortnight."}
          </p>
          <p className="text-pw-ink-700 mt-2 text-[13px] break-all">{link}</p>
        </div>
      ) : null}
    </div>
  );
}
