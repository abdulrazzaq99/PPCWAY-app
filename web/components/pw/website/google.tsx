"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Card, Note, Toggle } from "@/components/pw/create/kit";
import type { Choice, SiteSetup } from "./types";

/*
  What the website tells Google Ads. Two things, both the merchant's choice:
  jobs sent back against their ad clicks, and Google's own conversions fired by
  the PPCWay script for a form or a call, so Google's tag needs no separate
  set-up. Each says plainly what it changes in their account.
*/
export function GoogleSide({
  first,
  choices,
  reason,
}: {
  first: SiteSetup;
  choices: Choice[];
  reason: string;
}) {
  const router = useRouter();
  const [setup, setSetup] = useState(first);
  const [working, setWorking] = useState("");
  const [trouble, setTrouble] = useState("");
  const locked = !setup.may_change || !setup.connected;

  async function save(change: Partial<SiteSetup>, what: string) {
    setWorking(what);
    setTrouble("");
    try {
      const res = await fetch("/api/site/settings", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(change),
      });
      const said = (await res.json().catch(() => ({}))) as SiteSetup & { error?: string };
      if (!res.ok) {
        setTrouble(said.error ?? "That did not save.");
        return;
      }
      setSetup(said);
      // The leads list says "Save and send to Google Ads" only while sending
      // is on, and it reads that from the page: so the page reads again.
      router.refresh();
    } catch {
      setTrouble("PPCWay is not reachable right now.");
    } finally {
      setWorking("");
    }
  }

  return (
    <Card
      title="Google Ads"
      help="What your website tells Google Ads, so it looks for more customers like your best ones."
    >
      <div className="flex flex-col gap-5 px-6 py-5">
        {!setup.connected ? (
          <Note tone="warn">Connect Google Ads in Settings first.</Note>
        ) : !setup.may_change ? (
          <Note>Only somebody who may approve changes can change these.</Note>
        ) : null}

        <Toggle
          on={setup.send_jobs}
          disabled={locked || working === "jobs"}
          onChange={(next) => save({ send_jobs: next }, "jobs")}
          help={
            <>
              When you mark a lead as a job, PPCWay tells Google Ads which ad click brought it and
              what the job was worth. Turning this on creates a conversion action called{" "}
              <span className="font-semibold">Jobs from PPCWay leads</span> in your account and
              counts it towards bidding.
            </>
          }
        >
          {working === "jobs" ? "Setting it up in Google Ads" : "Send jobs to Google Ads"}
        </Toggle>

        <div className="border-pw-border flex flex-col gap-4 border-t pt-5">
          <p className="text-pw-ink-600 text-[13px] leading-[19px]">
            PPCWay can also count forms and calls in Google Ads itself, so Google&rsquo;s tag needs
            no separate set-up. Leave these off if Google&rsquo;s tag already counts them, or they
            will be counted twice.
          </p>
          <Pick
            label="When a form is sent, count it as"
            value={setup.form_send_to}
            choices={choices}
            disabled={locked || working === "form"}
            onChange={(v) => save({ form_send_to: v }, "form")}
          />
          <Pick
            label="When your phone number is tapped, count it as"
            value={setup.call_send_to}
            choices={choices}
            disabled={locked || working === "call"}
            onChange={(v) => save({ call_send_to: v }, "call")}
          />
          {setup.connected && !choices.length && reason ? (
            <p className="text-pw-ink-500 text-[13px]">{reason}</p>
          ) : null}
        </div>

        {trouble ? (
          <p className="text-pw-bad text-[13px]" role="alert">
            {trouble}
          </p>
        ) : null}
      </div>
    </Card>
  );
}

function Pick({
  label,
  value,
  choices,
  disabled,
  onChange,
}: {
  label: string;
  value: string;
  choices: Choice[];
  disabled: boolean;
  onChange: (value: string) => void;
}) {
  const known = choices.some((c) => c.send_to === value);
  return (
    <label className="flex flex-col gap-2">
      <span className="text-pw-ink text-[14px] font-medium">{label}</span>
      <select
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
        className="border-pw-border bg-pw-card text-pw-ink h-10 rounded-[10px] border px-3 text-[14px] disabled:opacity-60"
      >
        <option value="">Do not count it in Google Ads</option>
        {value && !known ? <option value={value}>{value}</option> : null}
        {choices.map((c) => (
          <option key={c.send_to} value={c.send_to}>
            {c.name}
            {c.category ? ` (${c.category})` : ""}
          </option>
        ))}
      </select>
    </label>
  );
}
