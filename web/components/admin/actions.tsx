"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

/*
  The controls. The panel had none, and a screen with no control for the job it
  exists for reads as a report rather than a tool.

  Each one is a disclosure rather than a button that fires: stopping writes
  across the platform is not something anybody should be one stray click away
  from, and the reason is required by the API anyway, so the form is where the
  reason gets typed. The button that does the thing is the second click, not
  the first.

  The outcome is reported in the panel, not in a toast. A toast for "writes are
  stopped" is a message about the most consequential state in the product
  disappearing after four seconds.
*/

const FIELD =
  "border-pw-border-input text-pw-ink placeholder:text-pw-ink-400 focus:border-pw-blue focus:ring-pw-blue/20 w-full rounded-[10px] border bg-white px-3 py-2 text-[14px] leading-[20px] outline-none focus:ring-2";

function Danger({ children, ...rest }: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      {...rest}
      className="bg-pw-bad-solid h-9 rounded-[10px] px-3 text-[14px] font-medium text-white transition-transform hover:brightness-110 active:scale-[0.98] disabled:opacity-60"
    >
      {children}
    </button>
  );
}

function Quiet({ children, ...rest }: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      {...rest}
      className="border-pw-border text-pw-ink-700 hover:bg-pw-row-hover h-9 rounded-[10px] border px-3 text-[14px] font-medium transition-transform active:scale-[0.98] disabled:opacity-60"
    >
      {children}
    </button>
  );
}

function Said({ trouble, good }: { trouble: string; good: string }) {
  if (!trouble && !good) return null;
  return (
    <p
      className={`mt-2 text-[13px] leading-[18px] ${trouble ? "text-pw-bad" : "text-pw-good"}`}
      role="status"
    >
      {trouble || good}
    </p>
  );
}

/* ---------- stop and release writes ---------- */

export function StopWrites({ stopped }: { stopped: boolean }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [because, setBecause] = useState("");
  const [working, setWorking] = useState(false);
  const [trouble, setTrouble] = useState("");
  const [good, setGood] = useState("");

  async function go(doing: "stop" | "release") {
    setWorking(true);
    setTrouble("");
    setGood("");
    try {
      const res = await fetch("/api/admin/platform", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ doing, because }),
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
        <Quiet onClick={() => go("release")} disabled={working}>
          {working ? "Letting writes resume…" : "Let writes resume"}
        </Quiet>
        <Said trouble={trouble} good={good} />
      </div>
    );
  }

  return (
    <div>
      {open ? (
        <div className="border-pw-border w-full max-w-[420px] rounded-[12px] border bg-white p-4">
          <label
            htmlFor="because"
            className="text-pw-ink block text-[13px] leading-[18px] font-medium"
          >
            Why are you stopping writes?
          </label>
          <p className="text-pw-ink-500 mt-0.5 text-[12px] leading-[16px]">
            Whoever picks this up reads this line. Twelve characters at least.
          </p>
          <input
            id="because"
            value={because}
            onChange={(e) => setBecause(e.target.value)}
            placeholder="A rule proposed nonsense overnight"
            className={`${FIELD} mt-2`}
          />
          <div className="mt-3 flex gap-2">
            <Danger onClick={() => go("stop")} disabled={working || because.trim().length < 12}>
              {working ? "Stopping…" : "Stop writes everywhere"}
            </Danger>
            <Quiet onClick={() => setOpen(false)} disabled={working}>
              Cancel
            </Quiet>
          </div>
          <Said trouble={trouble} good={good} />
        </div>
      ) : (
        <Quiet onClick={() => setOpen(true)}>Stop writes</Quiet>
      )}
      {!open ? <Said trouble={trouble} good={good} /> : null}
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
        <Quiet onClick={() => setOpen(true)}>Give somebody access</Quiet>
        <Said trouble={trouble} good={good} />
      </div>
    );
  }

  return (
    <div className="border-pw-border w-full max-w-[460px] rounded-[12px] border bg-white p-4">
      <div className="grid gap-3">
        <div>
          <label
            htmlFor="email"
            className="text-pw-ink block text-[13px] leading-[18px] font-medium"
          >
            Their email
          </label>
          <p className="text-pw-ink-500 mt-0.5 text-[12px] leading-[16px]">
            They have to have signed in once first.
          </p>
          <input
            id="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="dana@ppcway.com"
            className={`${FIELD} mt-2`}
          />
        </div>
        <div>
          <label
            htmlFor="level"
            className="text-pw-ink block text-[13px] leading-[18px] font-medium"
          >
            What they may do
          </label>
          <select
            id="level"
            value={level}
            onChange={(e) => setLevel(e.target.value)}
            className={`${FIELD} mt-2`}
          >
            <option value="support">Support, reads a merchant and changes nothing</option>
            <option value="engineer">Engineer, reads the platform and re-runs jobs</option>
            <option value="principal">Principal, stops writes and grants access</option>
          </select>
        </div>
        <div>
          <label htmlFor="why" className="text-pw-ink block text-[13px] leading-[18px] font-medium">
            Why
          </label>
          <input
            id="why"
            value={because}
            onChange={(e) => setBecause(e.target.value)}
            placeholder="Joining support on Monday"
            className={`${FIELD} mt-2`}
          />
        </div>
      </div>
      <div className="mt-3 flex gap-2">
        <button
          onClick={go}
          disabled={working || !email.trim() || !because.trim()}
          className="bg-pw-blue hover:bg-pw-blue-hover h-9 rounded-[10px] px-3 text-[14px] font-medium text-white transition-transform active:scale-[0.98] disabled:opacity-60"
        >
          {working ? "Giving access…" : "Give access"}
        </button>
        <Quiet onClick={() => setOpen(false)} disabled={working}>
          Cancel
        </Quiet>
      </div>
      <Said trouble={trouble} good={good} />
    </div>
  );
}
