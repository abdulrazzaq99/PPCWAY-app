"use client";

import Link from "next/link";
import { Button, LinkButton } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/field";
import { ManualForm } from "./manual-form";
import { AuditPage, Card, Pill } from "./shell";
import { StartAudit } from "./start-audit";

/*
  Frames 181:5823 (Find your business, with three matches), 181:5880 (Confirm your
  listing), 181:5920 (Checking) and 181:5971 (We could not find you).
  Static sample data; the live run starts from the not-found form, which is the one
  that carries a website today. A client component because Field takes a render
  function for its input, which cannot cross from a server component.
*/
export type Typed = { name: string; city: string; site: string };
const SAMPLE: Typed = { name: "Alpha Plumbing", city: "Mississauga, Ontario", site: "" };

export function AuditFindView({
  view,
  typed,
}: {
  view: "find" | "results" | "confirm" | "checking" | "not-found";
  typed?: Partial<Typed>;
}) {
  const t: Typed = { ...SAMPLE, ...typed };
  if (view === "confirm") return <ConfirmView typed={t} />;
  if (view === "checking") return <CheckingView />;
  if (view === "not-found") return <NotFoundView />;
  return <FindView results={view === "results"} typed={t} />;
}

function query(t: Typed, view: string): string {
  const q = new URLSearchParams({ view, name: t.name, city: t.city });
  if (t.site) q.set("site", t.site);
  return `/audit?${q.toString()}`;
}

function FindView({ results, typed }: { results: boolean; typed: Typed }) {
  return (
    <AuditPage>
      <Pill>Free audit, no account needed</Pill>
      <h1 className="mt-6 text-[32px] leading-[38px] font-bold text-balance sm:text-[42px] sm:leading-[51px]">
        Let us look at your business the way Google sees it.
      </h1>
      <p className="text-muted mt-6 max-w-[700px] text-[18px] leading-[22px]">
        Start with your name. We check your Google listing, your website and whether your ads are
        showing today, then tell you what is worth fixing first.
      </p>
      <Card className="mt-6 p-5 sm:p-7">
        <form action="/audit" method="get" className="flex flex-col gap-4">
          <input type="hidden" name="view" value="results" />
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Business name">
              {(id) => (
                <Input id={id} name="name" defaultValue={typed.name} autoComplete="organization" />
              )}
            </Field>
            <Field label="City or town">
              {(id) => (
                <Input
                  id={id}
                  name="city"
                  defaultValue={typed.city}
                  autoComplete="address-level2"
                />
              )}
            </Field>
          </div>
          <Field
            label="Website"
            hint="The page your ads would send people to. We read it and change nothing."
          >
            {(id) => (
              <Input
                id={id}
                name="site"
                defaultValue={typed.site}
                placeholder="alphaplumbing.ca"
                inputMode="url"
                autoComplete="url"
              />
            )}
          </Field>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-faint text-[14px] leading-[17px]">
              No card, no login. It takes about a minute.
            </p>
            <Button type="submit" size="sm" className="h-[42px]">
              Find my business
            </Button>
          </div>
        </form>
      </Card>
      {results ? (
        <div className="mt-6">
          <p className="text-muted text-[15px] leading-[18px] font-semibold">
            Three businesses match. Which one is yours?
          </p>
          <div className="mt-3 flex flex-col gap-3">
            <Result
              selected
              name="Alpha Plumbing"
              meta="1420 Dundas Street East, Mississauga · Plumber · Open now"
              chip="4.6 · 87 reviews"
            />
            <Result
              name="Alpha Plumbing & Drains"
              meta="Etobicoke, Toronto · Plumber"
              chip="3.9 · 12 reviews"
            />
            <Result
              name="Alpha Plumbing Services"
              meta="Brampton · Plumber · No hours listed"
              chip="No reviews yet"
            />
          </div>
          <div className="mt-5 flex flex-wrap items-center justify-between gap-4">
            <Link
              href="/audit?view=not-found"
              className="text-brand text-[14px] leading-[17px] font-semibold"
            >
              None of these are us
            </Link>
            <LinkButton href={query(typed, "confirm")} size="sm" className="h-[42px]">
              This one
            </LinkButton>
          </div>
        </div>
      ) : null}
    </AuditPage>
  );
}

function Result({
  name,
  meta,
  chip,
  selected,
}: {
  name: string;
  meta: string;
  chip: string;
  selected?: boolean;
}) {
  return (
    <label
      className={`flex cursor-pointer items-center gap-4 rounded-[12px] border px-4 py-4 ${selected ? "border-brand bg-brand-tint" : "border-line bg-panel hover:bg-line-soft"}`}
    >
      <input type="radio" name="listing" defaultChecked={selected} className="peer sr-only" />
      <span
        aria-hidden
        className={`flex size-[18px] shrink-0 items-center justify-center rounded-full border ${selected ? "border-brand" : "border-line-input"}`}
      >
        {selected ? <span className="bg-brand size-[9px] rounded-full" /> : null}
      </span>
      <span className="min-w-0 flex-1">
        <span className="text-ink block text-[16px] leading-[19px] font-semibold">{name}</span>
        <span className="text-faint mt-1 block text-[13px] leading-4">{meta}</span>
      </span>
      <Pill tone="grey">{chip}</Pill>
    </label>
  );
}

function ConfirmView({ typed }: { typed: Typed }) {
  return (
    <AuditPage>
      <h1 className="text-[32px] leading-[38px] font-bold sm:text-[42px] sm:leading-[51px]">
        Is this you?
      </h1>
      <p className="text-muted mt-6 max-w-[700px] text-[18px] leading-[22px]">
        Everything below comes from your Google Business Profile. If something looks wrong here, it
        looks wrong to your customers too.
      </p>
      <Card className="mt-6">
        <div className="flex flex-col gap-5 p-5 sm:flex-row sm:p-7">
          <div className="bg-bar-soft flex size-[132px] shrink-0 items-center justify-center rounded-[14px]">
            <span className="text-faint text-[13px] font-semibold">Photo</span>
          </div>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-[10px]">
              <span className="text-[24px] leading-[29px] font-bold">Alpha Plumbing</span>
              <Pill>Verified</Pill>
            </div>
            <p className="text-muted mt-[10px] text-[15px] leading-[18px]">
              Plumber · 1420 Dundas Street East, Mississauga, Ontario
            </p>
            <p className="text-muted mt-[10px] text-[15px] leading-[18px]">
              4.6 out of 5, from 87 reviews · Open now, closes 9 pm ·{" "}
              {typed.site || "alphaplumbing.ca"}
            </p>
            <div className="mt-[10px] flex flex-wrap gap-2">
              <Pill tone="grey">Emergency plumbing</Pill>
              <Pill tone="grey">Drain clearing</Pill>
              <Pill tone="grey">Water heaters</Pill>
            </div>
          </div>
        </div>
        <div className="border-line-soft flex flex-col gap-3 border-t px-5 py-5 sm:flex-row sm:items-center sm:justify-between sm:px-7">
          <Link
            href={query(typed, "results")}
            className="text-muted text-[14px] leading-[17px] font-semibold"
          >
            Not us. Search again
          </Link>
          <StartAudit
            business={typed.name}
            city={typed.city}
            site={typed.site}
            label="Yes, that is us. Check it"
          />
        </div>
      </Card>
      <p className="text-faint mt-6 text-[14px] leading-[17px]">
        We only read what is already public. Nothing is posted, changed or contacted.
      </p>
    </AuditPage>
  );
}

const STEPS = [
  {
    title: "Your Google listing",
    meta: "Category, hours, photos, reviews and what people ask you",
    state: "done",
  },
  {
    title: "Your website",
    meta: "Reading 12 pages: services, areas, phone numbers and tracking tags",
    state: "running",
  },
  {
    title: "Ads showing right now",
    meta: "Whether you or your competitors appear for the searches that matter",
    state: "todo",
  },
  {
    title: "Local competition",
    meta: "Who else advertises in Mississauga, and how you compare",
    state: "todo",
  },
] as const;

export function CheckingRows({
  steps = STEPS,
}: {
  steps?: readonly { title: string; meta: string; state: "done" | "running" | "todo" }[];
}) {
  return (
    <div className="divide-line-soft divide-y">
      {steps.map((s) => (
        <div key={s.title} className="flex items-center gap-[14px] py-4">
          <span
            className={`flex size-7 shrink-0 items-center justify-center rounded-full text-[14px] font-bold ${
              s.state === "done"
                ? "bg-brand-pale text-brand"
                : s.state === "running"
                  ? "bg-amber-tint text-amber"
                  : "bg-line-soft text-faint"
            }`}
          >
            {s.state === "done" ? "✓" : s.state === "running" ? "···" : ""}
          </span>
          <span className="min-w-0">
            <span
              className={`block text-[16px] leading-[19px] font-semibold ${s.state === "todo" ? "text-faint" : "text-ink"}`}
            >
              {s.title}
            </span>
            <span className="text-faint mt-[2px] block text-[13px] leading-4">{s.meta}</span>
          </span>
        </div>
      ))}
    </div>
  );
}

function CheckingView() {
  return (
    <AuditPage>
      <h1 className="text-[32px] leading-[38px] font-bold sm:text-[42px] sm:leading-[51px]">
        Checking Alpha Plumbing.
      </h1>
      <p className="text-muted mt-6 max-w-[700px] text-[18px] leading-[22px]">
        About forty seconds. You can stay on this page, or give us an email address and we will send
        the report when it is ready.
      </p>
      <Card className="mt-6 px-5 py-1 sm:px-7">
        <CheckingRows />
      </Card>
      <form
        className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-end"
        action="/audit/report"
        method="get"
      >
        <input type="hidden" name="view" value="advertising" />
        <Field label="Email me the report when it is done" className="flex-1">
          {(id) => (
            <Input
              id={id}
              type="email"
              name="email"
              placeholder="you@yourbusiness.ca"
              autoComplete="email"
            />
          )}
        </Field>
        <Button type="submit" variant="secondary" className="shrink-0">
          Email it to me
        </Button>
      </form>
    </AuditPage>
  );
}

function NotFoundView() {
  return (
    <AuditPage>
      <h1 className="text-[32px] leading-[38px] font-bold text-balance sm:text-[40px] sm:leading-[48px]">
        We could not find a listing for that name.
      </h1>
      <p className="text-muted mt-6 max-w-[720px] text-[18px] leading-[22px]">
        That usually means the business has no Google listing yet, or it is under a different name.
        Either is fine: tell us the basics and we will check what we can.
      </p>
      <Card className="mt-6 p-5 sm:p-7">
        <ManualForm />
      </Card>
    </AuditPage>
  );
}
