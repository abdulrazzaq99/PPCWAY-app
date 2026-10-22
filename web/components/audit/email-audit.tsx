"use client";

import { useState } from "react";

/*
  "Email me this audit", on a report that has already been run.

  It used to be a link to the waiting screen, which started the whole check
  again and asked for an address it then threw away. This sends what is on the
  screen and says where it went.

  One press is enough when we already know who is reading: the first try goes
  with no address at all, and the backend answers with the one it holds. It
  only asks for an address when nobody is signed in and the audit has none,
  which is the one case where we genuinely cannot know.
*/
const DARK =
  "border-night-line hover:bg-night-raised inline-flex h-[46px] items-center justify-center " +
  "rounded-[12px] border px-7 text-[15px] font-semibold text-white disabled:opacity-60";

export function EmailThisAudit({ runId }: { runId: string }) {
  const [email, setEmail] = useState("");
  const [asking, setAsking] = useState(false);
  const [busy, setBusy] = useState(false);
  const [sentTo, setSentTo] = useState("");
  const [trouble, setTrouble] = useState("");

  async function send() {
    setBusy(true);
    setTrouble("");
    try {
      const res = await fetch(`/api/audit/${encodeURIComponent(runId)}/email`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(email.trim() ? { email: email.trim() } : {}),
      });
      const said = (await res.json().catch(() => ({}))) as { sent_to?: string; error?: string };
      if (res.status === 400) {
        // Nobody signed in and no address on the audit: now we have to ask.
        setAsking(true);
        return;
      }
      if (!res.ok || !said.sent_to) {
        setTrouble(said.error ?? "That could not be sent.");
        return;
      }
      setSentTo(said.sent_to);
    } catch {
      setTrouble("We could not reach the service.");
    } finally {
      setBusy(false);
    }
  }

  if (sentTo) {
    return (
      <p className="text-night-faint text-[15px] leading-[22px]">
        Sent to <span className="font-semibold text-white">{sentTo}</span>. It is in your inbox
        within a minute, and the link in it opens this same report.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      {asking && (
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@yourbusiness.ca"
          autoComplete="email"
          className="border-night-line bg-night-raised placeholder:text-night-faint h-[46px] rounded-[12px] border px-4 text-[15px] text-white"
        />
      )}
      <button type="button" onClick={send} disabled={busy} className={DARK}>
        {busy ? "Sending…" : asking ? "Send it" : "Email me this audit"}
      </button>
      {asking && !trouble && (
        <p className="text-night-faint text-[13px] leading-[18px]">
          Where should it go? We send this report and nothing else.
        </p>
      )}
      {trouble && <p className="text-[13px] leading-[18px] text-amber-300">{trouble}</p>}
    </div>
  );
}
