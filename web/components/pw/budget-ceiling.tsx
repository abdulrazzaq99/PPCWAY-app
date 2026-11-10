"use client";

import { useState } from "react";
import { money } from "@/components/pw/campaigns";
import { PwCard } from "@/components/pw/shell";
import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/field";

/*
  The most any one campaign may be given to spend a day.

  Otto only suggests a bigger budget below this. With none set, it suggests
  none at all -- the guardrails refuse a rise they have nothing to measure
  against -- and the inbox says which campaign is waiting for one. Setting it
  writes a new version of the limits, so changes made before keep the limits
  that judged them.
*/
export type Limits = { max_daily_budget: number; currency: string; may_set: boolean };

export function BudgetCeiling({ initial }: { initial: Limits }) {
  const [saved, setSaved] = useState(initial.max_daily_budget);
  const [typed, setTyped] = useState(
    initial.max_daily_budget > 0 ? String(initial.max_daily_budget) : "",
  );
  const [busy, setBusy] = useState(false);
  const [said, setSaid] = useState("");
  const [trouble, setTrouble] = useState("");
  const amount = Number(typed || "0");
  const changed = amount !== saved && amount >= 0 && !Number.isNaN(amount);

  const save = async () => {
    setBusy(true);
    setSaid("");
    setTrouble("");
    try {
      const res = await fetch("/api/otto/limits", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ max_daily_budget: amount }),
      });
      const answer = (await res.json().catch(() => ({}))) as Partial<Limits> & {
        error?: string;
      };
      if (!res.ok) {
        setTrouble(answer.error ?? "That did not work.");
        return;
      }
      setSaved(answer.max_daily_budget ?? amount);
      setSaid(
        amount > 0
          ? `Saved. Otto may now suggest budgets up to ${money(amount, initial.currency)} a day.`
          : "Saved. Otto will not suggest a bigger budget for any campaign.",
      );
    } catch {
      setTrouble("PPCWay is not reachable right now. Nothing was changed.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <PwCard className="p-5 sm:p-6">
      <h2 className="text-[17px] leading-[22px] font-semibold">Budget ceiling for Otto</h2>
      <p className="text-pw-ink-500 mt-1 max-w-[680px] text-[14px] leading-[20px]">
        The most Otto may ever suggest a single campaign spends in a day. Without one, Otto never
        suggests a bigger budget, only smaller ones. You still approve every change.
      </p>
      <div className="mt-4 flex flex-wrap items-end gap-3">
        <Field label="The most a campaign may spend a day">
          {(id) => (
            <Input
              id={id}
              inputMode="decimal"
              value={typed}
              disabled={!initial.may_set || busy}
              placeholder="Not set"
              onChange={(e) => setTyped(e.target.value.replace(/[^0-9.]/g, ""))}
              trailing={<span className="text-pw-ink-500 text-[14px]">{initial.currency}</span>}
              className="w-[220px]"
            />
          )}
        </Field>
        {initial.may_set ? (
          <Button onClick={save} disabled={!changed || busy}>
            {busy ? "Saving…" : "Save"}
          </Button>
        ) : null}
      </div>
      <p className="text-pw-ink-700 mt-3 text-[14px] leading-[20px]" aria-live="polite">
        {!initial.may_set
          ? "Only the owner of the business can change this."
          : trouble ||
            said ||
            (saved > 0
              ? `Set at ${money(saved, initial.currency)} a day.`
              : "Not set yet, so Otto suggests no budget rises.")}
      </p>
      {trouble ? <span className="sr-only">{trouble}</span> : null}
    </PwCard>
  );
}
