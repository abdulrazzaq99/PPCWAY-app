"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { BUTTON, FIELD } from "./ui";

/*
  The console's two controls that change something.

  Each is a disclosure rather than a button that fires. Stopping writes is not
  something anybody should be one stray click away from, and the API wants a
  reason anyway, so the form is where the reason is typed and the button that
  does the thing is the second click, not the first. It names what it stops,
  so nobody confirms "stop" without reading which door they are closing.

  The outcome is said in place, not in a toast. "Writes are stopped" is a
  message about the most consequential state in the product, and it should
  not disappear after four seconds.
*/

function Said({ trouble, good }: { trouble: string; good: string }) {
  if (!trouble && !good) return null;
  return (
    <p
      role="status"
      className={`mt-2 text-[12px] leading-[18px] ${trouble ? "text-ad-negative" : "text-ad-positive"}`}
    >
      {trouble || good}
    </p>
  );
}

/* ---------- stop and release writes ---------- */

export function StopWrites({
  stopped,
  customerId = "",
  label,
}: {
  stopped: boolean;
  /* Empty stops every account; an id stops that one alone. */
  customerId?: string;
  label: string;
}) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [because, setBecause] = useState("");
  const [working, setWorking] = useState(false);
  const [trouble, setTrouble] = useState("");
  const [good, setGood] = useState("");
  const scope = customerId ? "this account" : "every account";

  async function go(doing: "stop" | "release") {
    setWorking(true);
    setTrouble("");
    setGood("");
    try {
      const res = await fetch("/api/admin/platform", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ doing, because, customer_id: customerId }),
      });
      const said = (await res.json().catch(() => ({}))) as { error?: string; words?: string };
      if (!res.ok) {
        setTrouble(said.error ?? "That did not work.");
        return;
      }
      setGood(said.words ?? "Done.");
      setOpen(false);
      setBecause("");
      router.refresh();
    } catch {
      setTrouble("The API is not reachable.");
    } finally {
      setWorking(false);
    }
  }

  if (stopped) {
    return (
      <div>
        <button
          type="button"
          onClick={() => go("release")}
          disabled={working}
          className={BUTTON.quiet}
        >
          {working ? "Letting writes resume…" : `Let writes resume on ${scope}`}
        </button>
        <Said trouble={trouble} good={good} />
      </div>
    );
  }

  if (!open) {
    return (
      <div>
        <button type="button" onClick={() => setOpen(true)} className={BUTTON.danger}>
          {label}
        </button>
        <Said trouble={trouble} good={good} />
      </div>
    );
  }

  const ready = because.trim().length >= 12;
  return (
    <div className="border-ad-border bg-ad-surface w-full max-w-[440px] rounded-[6px] border p-4">
      <label htmlFor={`because-${customerId || "all"}`} className="block text-[13px] font-medium">
        Why are you stopping writes on {scope}?
      </label>
      <p
        id={`because-help-${customerId || "all"}`}
        className="text-ad-faint mt-0.5 text-[12px] leading-[18px]"
      >
        Whoever picks this up reads this line. Twelve characters at least.
      </p>
      <input
        id={`because-${customerId || "all"}`}
        aria-describedby={`because-help-${customerId || "all"}`}
        value={because}
        onChange={(e) => setBecause(e.target.value)}
        placeholder="A rule proposed nonsense overnight"
        className={`${FIELD} mt-2`}
        autoFocus
      />
      <div className="mt-3 flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => go("stop")}
          disabled={working || !ready}
          className={BUTTON.danger}
        >
          {working ? "Stopping…" : `Stop writes on ${scope}`}
        </button>
        <button
          type="button"
          onClick={() => setOpen(false)}
          disabled={working}
          className={BUTTON.quiet}
        >
          Cancel
        </button>
      </div>
      <Said trouble={trouble} good={good} />
    </div>
  );
}

/* ---------- switch writes on and off ---------- */

/*
  The write gate, as a switch. The owner asked for it so that testing does not
  need a redeploy for every on and off.

  Off is one click: nobody should hesitate to stop. On is two, and the second
  only after a reason is typed, because it is the direction that changes what
  happens to a merchant's money, and the reason is kept with your name. The
  switch does not move until the API says it has, so the screen never shows a
  state the platform is not in.
*/
export function SwitchWrites({ on, may }: { on: boolean; may: boolean }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [because, setBecause] = useState("");
  const [working, setWorking] = useState(false);
  const [trouble, setTrouble] = useState("");
  const [good, setGood] = useState("");

  async function go(next: boolean) {
    setWorking(true);
    setTrouble("");
    setGood("");
    try {
      const res = await fetch("/api/admin/platform", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ doing: "writes", on: next, because }),
      });
      const said = (await res.json().catch(() => ({}))) as { error?: string; words?: string };
      if (!res.ok) {
        setTrouble(said.error ?? "That did not work.");
        return;
      }
      setGood(said.words ?? "Done.");
      setOpen(false);
      setBecause("");
      router.refresh();
    } catch {
      setTrouble("The API is not reachable.");
    } finally {
      setWorking(false);
    }
  }

  const ready = because.trim().length >= 12;
  return (
    <div>
      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          role="switch"
          aria-checked={on}
          aria-label="Writes to Google Ads"
          disabled={!may || working}
          onClick={() => (on ? go(false) : setOpen((was) => !was))}
          className={`relative inline-flex h-[24px] w-[44px] flex-none items-center rounded-full border transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-50 ${
            on ? "border-ad-positive bg-ad-positive" : "border-ad-control bg-ad-ground"
          }`}
        >
          <span
            aria-hidden
            className={`bg-ad-text inline-block h-[18px] w-[18px] rounded-full shadow transition-transform duration-150 ${
              on ? "translate-x-[22px]" : "translate-x-[2px]"
            }`}
          />
        </button>
        <span className="text-[13px] font-medium">
          {working ? (on ? "Switching off…" : "Switching on…") : on ? "On" : "Off"}
        </span>
      </div>
      {!may ? (
        <p className="text-ad-faint mt-2 text-[12px] leading-[18px]">
          Only principal access can switch writes on or off.
        </p>
      ) : null}

      {open && !on ? (
        <div className="border-ad-border bg-ad-ground mt-3 w-full max-w-[440px] rounded-[6px] border p-4">
          <label htmlFor="writes-because" className="block text-[13px] font-medium">
            Why are you switching writes on?
          </label>
          <p id="writes-because-help" className="text-ad-faint mt-0.5 text-[12px] leading-[18px]">
            Approved changes start going to merchants’ Google Ads accounts, each checked again
            first. Kept with your name. Twelve characters at least.
          </p>
          <input
            id="writes-because"
            aria-describedby="writes-because-help"
            value={because}
            onChange={(e) => setBecause(e.target.value)}
            placeholder="Testing the write path on the test account"
            className={`${FIELD} mt-2`}
            autoFocus
          />
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => go(true)}
              disabled={working || !ready}
              className={BUTTON.primary}
            >
              {working ? "Switching on…" : "Start writing to Google Ads"}
            </button>
            <button
              type="button"
              onClick={() => setOpen(false)}
              disabled={working}
              className={BUTTON.quiet}
            >
              Cancel
            </button>
          </div>
        </div>
      ) : null}
      <Said trouble={trouble} good={good} />
    </div>
  );
}

/* ---------- grant access ---------- */

export function GrantAccess() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [email, setEmail] = useState("");
  const [level, setLevel] = useState("support");
  const [because, setBecause] = useState("");
  const [working, setWorking] = useState(false);
  const [trouble, setTrouble] = useState("");
  const [good, setGood] = useState("");

  async function go() {
    setWorking(true);
    setTrouble("");
    setGood("");
    try {
      const res = await fetch("/api/admin/staff", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ email, level, because }),
      });
      const said = (await res.json().catch(() => ({}))) as { error?: string; words?: string };
      if (!res.ok) {
        setTrouble(said.error ?? "That did not work.");
        return;
      }
      setGood(said.words ?? "Done.");
      setEmail("");
      setBecause("");
      setOpen(false);
      router.refresh();
    } catch {
      setTrouble("The API is not reachable.");
    } finally {
      setWorking(false);
    }
  }

  if (!open) {
    return (
      <div>
        <button type="button" onClick={() => setOpen(true)} className={BUTTON.primary}>
          Give somebody access
        </button>
        <Said trouble={trouble} good={good} />
      </div>
    );
  }

  return (
    <div className="border-ad-border bg-ad-surface w-full max-w-[460px] rounded-[6px] border p-4">
      <div className="grid gap-4">
        <div>
          <label htmlFor="grant-email" className="block text-[13px] font-medium">
            Their email
          </label>
          <p id="grant-email-help" className="text-ad-faint mt-0.5 text-[12px] leading-[18px]">
            They have to have signed in once first.
          </p>
          <input
            id="grant-email"
            type="email"
            aria-describedby="grant-email-help"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="dana@ppcway.com"
            className={`${FIELD} mt-2`}
            autoFocus
          />
        </div>
        <div>
          <label htmlFor="grant-level" className="block text-[13px] font-medium">
            What they may do
          </label>
          <select
            id="grant-level"
            value={level}
            onChange={(e) => setLevel(e.target.value)}
            className={`${FIELD} mt-2`}
          >
            <option value="support">Support: reads a merchant, changes nothing</option>
            <option value="engineer">Engineer: reads the platform, re-runs jobs</option>
            <option value="principal">Principal: stops writes, grants access</option>
          </select>
        </div>
        <div>
          <label htmlFor="grant-why" className="block text-[13px] font-medium">
            Why
          </label>
          <input
            id="grant-why"
            value={because}
            onChange={(e) => setBecause(e.target.value)}
            placeholder="Joining support on Monday"
            className={`${FIELD} mt-2`}
          />
        </div>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <button
          type="button"
          onClick={go}
          disabled={working || !email.trim() || !because.trim()}
          className={BUTTON.primary}
        >
          {working ? "Giving access…" : "Give access"}
        </button>
        <button
          type="button"
          onClick={() => setOpen(false)}
          disabled={working}
          className={BUTTON.quiet}
        >
          Cancel
        </button>
      </div>
      <Said trouble={trouble} good={good} />
    </div>
  );
}
