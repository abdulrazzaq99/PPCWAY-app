"use client";

import { EnvelopeSimpleIcon, NotePencilIcon, PhoneIcon } from "@phosphor-icons/react";
import { useState } from "react";
import { Card } from "@/components/pw/create/kit";
import { Chip } from "@/components/pw/shell";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/cn";
import { ago } from "./install";
import type { Lead } from "./types";

/*
  The people who got in touch from the website, newest first, and the one
  question only the merchant can answer about each: did it become a job? A job
  marked here goes to Google Ads against the ad click that brought it, when
  sending is switched on, and the line under it says what became of that.
*/
type Filter = "" | "job" | "not_job" | "spam";

const FILTERS: [Filter, string][] = [
  ["", "All"],
  ["job", "Jobs"],
  ["not_job", "Not jobs"],
  ["spam", "Spam"],
];

export function Leads({
  first,
  mayChange,
  sending,
  currency,
}: {
  first: Lead[];
  mayChange: boolean;
  sending: boolean;
  currency: string;
}) {
  const [filter, setFilter] = useState<Filter>("");
  const [leads, setLeads] = useState<Lead[]>(first);
  const [loading, setLoading] = useState(false);
  const [trouble, setTrouble] = useState("");

  async function show(next: Filter) {
    setFilter(next);
    setLoading(true);
    setTrouble("");
    try {
      const res = await fetch(`/api/site/leads${next ? `?status=${next}` : ""}`);
      const said = (await res.json().catch(() => ({}))) as { leads?: Lead[]; error?: string };
      if (res.ok) setLeads(said.leads ?? []);
      else setTrouble(said.error ?? "The leads could not be read just now.");
    } catch {
      setTrouble("PPCWay is not reachable right now.");
    } finally {
      setLoading(false);
    }
  }

  function changed(lead: Lead) {
    setLeads((now) =>
      now
        .map((one) => (one.id === lead.id ? lead : one))
        // A lead marked into another list leaves this one, except "All",
        // which shows everything but spam.
        .filter((one) => (filter ? one.status === filter : one.status !== "spam")),
    );
  }

  return (
    <Card
      title="Leads from your website"
      help="Forms sent, phone numbers and email addresses tapped. Mark the ones that became jobs."
    >
      <div className="px-6 pt-4">
        <div className="bg-pw-muted inline-flex flex-wrap gap-1 rounded-[12px] p-[4px]">
          {FILTERS.map(([value, label]) => (
            <button
              key={value || "all"}
              type="button"
              onClick={() => show(value)}
              aria-pressed={filter === value}
              className={cn(
                "rounded-[9px] px-3 py-[6px] text-[13px] font-semibold",
                filter === value ? "bg-pw-card text-pw-ink shadow-sm" : "text-pw-ink-500",
              )}
            >
              {label}
            </button>
          ))}
        </div>
      </div>
      {trouble ? (
        <p className="text-pw-bad px-6 py-4 text-[14px]" role="alert">
          {trouble}
        </p>
      ) : null}
      {loading ? (
        <p className="text-pw-ink-500 px-6 py-6 text-[14px]">Reading the leads</p>
      ) : leads.length === 0 ? (
        <p className="text-pw-ink-500 px-6 py-8 text-[14px] leading-[20px]">
          {filter
            ? "None here yet."
            : "No leads yet. When somebody sends a form or taps your phone number on your website, they appear here within a minute."}
        </p>
      ) : (
        <ul className="divide-pw-border divide-y">
          {leads.map((lead) => (
            <LeadRow
              key={lead.id}
              lead={lead}
              mayChange={mayChange}
              sending={sending}
              currency={currency}
              onChange={changed}
            />
          ))}
        </ul>
      )}
    </Card>
  );
}

const DID = {
  form: "sent a form",
  call: "tapped your phone number",
  email: "tapped your email address",
} as const;

function LeadRow({
  lead,
  mayChange,
  sending,
  currency,
  onChange,
}: {
  lead: Lead;
  mayChange: boolean;
  sending: boolean;
  currency: string;
  onChange: (lead: Lead) => void;
}) {
  const [asking, setAsking] = useState(false);
  const [value, setValue] = useState(lead.value != null ? String(lead.value) : "");
  const [working, setWorking] = useState("");
  const [trouble, setTrouble] = useState("");
  const [opened, setOpened] = useState(false);
  const Icon =
    lead.kind === "call" ? PhoneIcon : lead.kind === "email" ? EnvelopeSimpleIcon : NotePencilIcon;
  const who = lead.name || lead.email || lead.phone || "Somebody";

  async function mark(status: Lead["status"]) {
    setWorking(status);
    setTrouble("");
    try {
      const res = await fetch(`/api/site/leads/${lead.id}`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ status, value: status === "job" ? value : null }),
      });
      const said = (await res.json().catch(() => ({}))) as Lead & { error?: string };
      if (!res.ok) {
        setTrouble(said.error ?? "That did not save.");
        return;
      }
      setAsking(false);
      onChange(said);
    } catch {
      setTrouble("PPCWay is not reachable right now.");
    } finally {
      setWorking("");
    }
  }

  return (
    <li className="flex flex-col gap-3 px-6 py-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-3">
          <span className="bg-pw-blue-tint text-pw-blue-ink mt-[2px] flex size-8 shrink-0 items-center justify-center rounded-full">
            <Icon className="size-4" weight="bold" />
          </span>
          <div className="min-w-0">
            <p className="text-pw-ink text-[15px] leading-[20px]">
              <span className="font-semibold">{who}</span> {DID[lead.kind]}
              {lead.page && lead.page !== "/" ? (
                <span className="text-pw-ink-500"> on {lead.page}</span>
              ) : null}
            </p>
            <p className="text-pw-ink-500 mt-1 flex flex-wrap items-center gap-2 text-[13px] leading-[18px]">
              <span suppressHydrationWarning>{ago(lead.created_at)}</span>
              <Chip tone={lead.from_ad ? "info" : "neutral"}>{lead.source_label}</Chip>
              {lead.campaign ? <span>{lead.campaign}</span> : null}
            </p>
          </div>
        </div>
        <Standing lead={lead} />
      </div>

      {lead.phone || lead.email ? (
        <p className="text-pw-ink-700 flex flex-wrap gap-x-5 gap-y-1 pl-11 text-[14px]">
          {lead.phone ? (
            <a className="text-pw-blue font-semibold" href={`tel:${lead.phone}`}>
              {lead.phone}
            </a>
          ) : null}
          {lead.email ? (
            <a className="text-pw-blue font-semibold" href={`mailto:${lead.email}`}>
              {lead.email}
            </a>
          ) : null}
        </p>
      ) : null}

      {lead.fields.length ? (
        <div className="pl-11">
          <button
            type="button"
            onClick={() => setOpened((o) => !o)}
            className="text-pw-blue hover:text-pw-blue-hover text-[13px] font-semibold"
            aria-expanded={opened}
          >
            {opened ? "Hide what they wrote" : "What they wrote"}
          </button>
          {opened ? (
            <dl className="border-pw-border mt-2 grid gap-x-4 gap-y-1 rounded-[12px] border p-3 text-[13px] leading-[19px] sm:grid-cols-[160px_1fr]">
              {lead.fields.map(([label, said], i) => (
                <div key={i} className="contents">
                  <dt className="text-pw-ink-500">{label}</dt>
                  <dd className="text-pw-ink break-words whitespace-pre-wrap">{said}</dd>
                </div>
              ))}
            </dl>
          ) : null}
        </div>
      ) : null}

      {lead.upload ? <Upload lead={lead} /> : null}

      {mayChange ? (
        <div className="flex flex-wrap items-center gap-2 pl-11">
          {asking ? (
            <>
              <label className="text-pw-ink-600 flex items-center gap-2 text-[13px]">
                What was it worth?
                <span className="border-pw-border bg-pw-card flex h-9 items-center rounded-[10px] border px-2">
                  <span className="text-pw-ink-400 pr-1 text-[13px]">{currency}</span>
                  <input
                    inputMode="decimal"
                    value={value}
                    onChange={(e) => setValue(e.target.value.replace(/[^\d.]/g, ""))}
                    placeholder="optional"
                    className="w-24 bg-transparent text-[14px] outline-none"
                    aria-label={`What the job was worth, in ${currency}`}
                  />
                </span>
              </label>
              <Button size="sm" onClick={() => mark("job")} working={working === "job" && "Saving"}>
                {sending ? "Save and send to Google Ads" : "Save"}
              </Button>
              <Button size="sm" variant="quiet" onClick={() => setAsking(false)}>
                Cancel
              </Button>
            </>
          ) : (
            <>
              {lead.status !== "job" ? (
                <Button size="sm" variant="secondary" onClick={() => setAsking(true)}>
                  It became a job
                </Button>
              ) : null}
              {lead.status !== "not_job" ? (
                <Button
                  size="sm"
                  variant="quiet"
                  onClick={() => mark("not_job")}
                  working={working === "not_job" && "Saving"}
                >
                  Not a job
                </Button>
              ) : null}
              {lead.status !== "spam" ? (
                <Button
                  size="sm"
                  variant="quiet"
                  onClick={() => mark("spam")}
                  working={working === "spam" && "Saving"}
                >
                  Spam
                </Button>
              ) : (
                <Button size="sm" variant="quiet" onClick={() => mark("new")}>
                  Not spam
                </Button>
              )}
            </>
          )}
          {trouble ? (
            <span className="text-pw-bad text-[13px]" role="alert">
              {trouble}
            </span>
          ) : null}
        </div>
      ) : null}
    </li>
  );
}

function Standing({ lead }: { lead: Lead }) {
  if (lead.status === "job") {
    const worth =
      lead.value != null
        ? ` · ${new Intl.NumberFormat("en-CA", { style: "currency", currency: lead.currency || "CAD", maximumFractionDigits: 0 }).format(lead.value)}`
        : "";
    return <Chip tone="good">{`Job${worth}`}</Chip>;
  }
  if (lead.status === "not_job") return <Chip tone="neutral">Not a job</Chip>;
  if (lead.status === "spam") return <Chip tone="bad">Spam</Chip>;
  return <Chip tone="otto">New</Chip>;
}

function Upload({ lead }: { lead: Lead }) {
  const words = {
    sent: "Sent to Google Ads.",
    waiting: lead.upload_note || "Waiting to go to Google Ads.",
    failed: `Google Ads did not take it: ${lead.upload_note}`,
    no_click: lead.upload_note,
  }[lead.upload as Exclude<Lead["upload"], "">];
  return (
    <p
      className={cn(
        "pl-11 text-[13px] leading-[18px]",
        lead.upload === "sent" && "text-pw-good",
        lead.upload === "waiting" && "text-pw-warn",
        lead.upload === "failed" && "text-pw-bad",
        lead.upload === "no_click" && "text-pw-ink-500",
      )}
    >
      {words}
    </p>
  );
}
