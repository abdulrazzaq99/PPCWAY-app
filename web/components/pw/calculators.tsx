"use client";

import { useState } from "react";
import { Chip, PwCard } from "@/components/pw/shell";

/*
  The three free tools in the sidebar. The handoff leaves them as placeholder
  links; they are arithmetic a business owner can check on paper, which makes
  them the one part of this app that can be real before anything is connected.

  Google's own limits for a responsive search ad are what the copy checker
  measures: 30 characters a headline, 90 a description.
*/
const HEADLINE_MAX = 30;
const DESCRIPTION_MAX = 90;

function Field({
  label,
  value,
  onChange,
  prefix,
  suffix,
  hint,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  prefix?: string;
  suffix?: string;
  hint?: string;
}) {
  return (
    <label className="flex flex-col gap-[6px]">
      <span className="text-[14px] font-semibold">{label}</span>
      <span className="border-pw-border-input bg-pw-card focus-within:border-pw-blue flex h-[44px] items-center gap-2 rounded-[12px] border px-3">
        {prefix ? <span className="text-pw-ink-400 text-[15px]">{prefix}</span> : null}
        <input
          inputMode="decimal"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="pw-num w-full bg-transparent text-[16px] outline-none"
        />
        {suffix ? <span className="text-pw-ink-400 text-[14px]">{suffix}</span> : null}
      </span>
      {hint ? <span className="text-pw-ink-400 text-[13px]">{hint}</span> : null}
    </label>
  );
}

function num(text: string): number {
  const n = Number.parseFloat(text.replace(/[^0-9.]/g, ""));
  return Number.isFinite(n) ? n : 0;
}

function money(n: number): string {
  return `$${n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function BudgetCalculator() {
  const [daily, setDaily] = useState("40");
  const [cpc, setCpc] = useState("4.50");
  const [rate, setRate] = useState("8");

  const monthly = num(daily) * 30.4;
  const clicks = num(cpc) > 0 ? Math.round(monthly / num(cpc)) : 0;
  const leads = Math.round(clicks * (num(rate) / 100));
  const perLead = leads > 0 ? monthly / leads : 0;

  return (
    <>
      <PwCard className="p-5 sm:p-6">
        <p className="text-pw-ink-500 max-w-[680px] text-[15px] leading-[23px]">
          What a daily budget turns into over a month. Google may spend up to twice your daily
          budget on a busy day and less on a quiet one, so judge it by the month, not the day.
        </p>
        <div className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-3">
          <Field label="Budget a day" value={daily} onChange={setDaily} prefix="$" />
          <Field
            label="Cost per click"
            value={cpc}
            onChange={setCpc}
            prefix="$"
            hint="Your audit shows this for your trade and town"
          />
          <Field
            label="Clicks that enquire"
            value={rate}
            onChange={setRate}
            suffix="%"
            hint="5 to 10% is ordinary for a trade"
          />
        </div>
      </PwCard>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Out label="A month" value={money(monthly)} note="30.4 days, which is what Google bills" />
        <Out label="Clicks a month" value={clicks.toLocaleString()} />
        <Out
          label="Enquiries a month"
          value={String(leads)}
          note={leads > 0 ? `about ${money(perLead)} each` : "raise the budget or the rate"}
        />
      </div>
    </>
  );
}

export function LeadCalculator() {
  const [spend, setSpend] = useState("1200");
  const [leads, setLeads] = useState("28");
  const [win, setWin] = useState("35");
  const [job, setJob] = useState("420");

  const perLead = num(leads) > 0 ? num(spend) / num(leads) : 0;
  const jobs = num(leads) * (num(win) / 100);
  const revenue = jobs * num(job);
  const roas = num(spend) > 0 ? revenue / num(spend) : 0;
  const perJob = jobs > 0 ? num(spend) / jobs : 0;

  return (
    <>
      <PwCard className="p-5 sm:p-6">
        <p className="text-pw-ink-500 max-w-[680px] text-[15px] leading-[23px]">
          What a lead costs, what a customer costs, and what comes back for every pound spent. The
          two numbers only you know are how many enquiries you win, and what a job is worth.
        </p>
        <div className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <Field label="Spend" value={spend} onChange={setSpend} prefix="$" hint="Last month" />
          <Field label="Enquiries" value={leads} onChange={setLeads} />
          <Field label="You win" value={win} onChange={setWin} suffix="%" />
          <Field label="A job is worth" value={job} onChange={setJob} prefix="$" />
        </div>
      </PwCard>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Out label="Cost per enquiry" value={perLead > 0 ? money(perLead) : "—"} />
        <Out label="Cost per customer" value={perJob > 0 ? money(perJob) : "—"} />
        <Out label="Revenue" value={money(revenue)} note={`${jobs.toFixed(1)} jobs`} />
        <Out
          label="Back for every $1"
          value={roas > 0 ? `${roas.toFixed(2)}×` : "—"}
          note={roas >= 1 ? "more out than in" : "more in than out"}
        />
      </div>
    </>
  );
}

export function AdCopyChecker() {
  const [headlines, setHeadlines] = useState(
    "Emergency Plumber in Oakville\n24/7 Call-Out\nNo Call-Out Fee",
  );
  const [descriptions, setDescriptions] = useState(
    "Burst pipe or blocked drain? We answer the phone day and night and quote before we start.",
  );

  const heads = headlines.split("\n").filter((l) => l.trim());
  const descs = descriptions.split("\n").filter((l) => l.trim());

  return (
    <>
      <PwCard className="p-5 sm:p-6">
        <p className="text-pw-ink-500 max-w-[680px] text-[15px] leading-[23px]">
          Google cuts a headline at {HEADLINE_MAX} characters and a description at {DESCRIPTION_MAX}
          , and refuses ads that shout. One line each.
        </p>
        <div className="mt-5 grid grid-cols-1 gap-4 lg:grid-cols-2">
          <label className="flex flex-col gap-[6px]">
            <span className="text-[14px] font-semibold">Headlines</span>
            <textarea
              value={headlines}
              onChange={(e) => setHeadlines(e.target.value)}
              rows={6}
              className="border-pw-border-input bg-pw-card focus:border-pw-blue rounded-[12px] border p-3 text-[15px] outline-none"
            />
          </label>
          <label className="flex flex-col gap-[6px]">
            <span className="text-[14px] font-semibold">Descriptions</span>
            <textarea
              value={descriptions}
              onChange={(e) => setDescriptions(e.target.value)}
              rows={6}
              className="border-pw-border-input bg-pw-card focus:border-pw-blue rounded-[12px] border p-3 text-[15px] outline-none"
            />
          </label>
        </div>
      </PwCard>

      <PwCard className="p-5 sm:p-6">
        <h2 className="text-[17px] font-semibold">What Google will make of it</h2>
        <ul className="mt-4 flex flex-col gap-2">
          {[
            ...heads.map((t) => ({ t, max: HEADLINE_MAX, kind: "Headline" })),
            ...descs.map((t) => ({ t, max: DESCRIPTION_MAX, kind: "Description" })),
          ].map(({ t, max, kind }, i) => {
            const over = t.length > max;
            const shouty = t.replace(/[^A-Z]/g, "").length > t.replace(/\s/g, "").length / 2;
            return (
              <li
                key={`${kind}-${i}`}
                className="border-pw-divider flex flex-wrap items-center justify-between gap-3 border-b py-2 last:border-0"
              >
                <span className="min-w-0 flex-1 truncate text-[15px]">{t}</span>
                <span className="flex items-center gap-2">
                  {shouty ? <Chip tone="warn">Too many capitals</Chip> : null}
                  <Chip tone={over ? "bad" : "good"}>
                    {t.length} of {max}
                  </Chip>
                </span>
              </li>
            );
          })}
        </ul>
        <p className="text-pw-ink-400 mt-4 text-[13px] leading-[20px]">
          Length and shouting are what can be checked here. Whether a claim is allowed &mdash;
          &ldquo;best&rdquo;, &ldquo;guaranteed&rdquo;, anything about price &mdash; is
          Google&rsquo;s call, and the audit reads the verdict from your account once it is
          connected.
        </p>
      </PwCard>
    </>
  );
}

function Out({ label, value, note }: { label: string; value: string; note?: string }) {
  return (
    <PwCard className="p-5">
      <p className="text-[14px] font-semibold">{label}</p>
      <p className="pw-num display mt-2 text-[30px] leading-[36px] font-semibold">{value}</p>
      {note ? <p className="text-pw-ink-500 mt-1 text-[13px]">{note}</p> : null}
    </PwCard>
  );
}
