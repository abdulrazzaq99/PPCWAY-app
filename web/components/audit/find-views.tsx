"use client";

import Link from "next/link";
import { useState } from "react";
import { Button, LinkButton } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/field";
import type { Listing } from "@/lib/listing";
import { listingMeta, listingRating } from "@/lib/listing";
import { ManualForm } from "./manual-form";
import { NameField } from "./name-field";
import { AuditPage, Card, Pill } from "./shell";
import { StartAudit } from "./start-audit";

/*
  Frames 181:5823 (Find your business, with three matches), 181:5880 (Confirm your
  listing), 181:5920 (Checking) and 181:5971 (We could not find you).

  With `listings` or `chosen` the screens show what Google returned; with neither
  they fall back to the drawn sample, which is how the frames are reviewed. The
  frames' Verified badge and service chips are gone: Google publishes neither, and
  only the owner's own sign-in would.
*/
export type Typed = { name: string; city: string; site: string };
const SAMPLE: Typed = { name: "Alpha Plumbing", city: "Mississauga, Ontario", site: "" };

const SAMPLE_MATCHES = [
  {
    name: "Alpha Plumbing",
    meta: "1420 Dundas Street East, Mississauga · Plumber · Open now",
    chip: "4.6 · 87 reviews",
  },
  {
    name: "Alpha Plumbing & Drains",
    meta: "Etobicoke, Toronto · Plumber",
    chip: "3.9 · 12 reviews",
  },
  {
    name: "Alpha Plumbing Services",
    meta: "Brampton · Plumber · No hours listed",
    chip: "No reviews yet",
  },
];

export function AuditFindView({
  view,
  typed,
  listings,
  chosen,
  error,
}: {
  view: "find" | "results" | "confirm" | "checking" | "not-found";
  typed?: Partial<Typed>;
  listings?: Listing[];
  chosen?: Listing;
  error?: string;
}) {
  const t: Typed = { ...SAMPLE, ...typed };
  // The form starts empty: the sample business belongs to the drawn states, and a
  // visitor should never find somebody else's name already in the box.
  const given: Typed = {
    name: typed?.name ?? "",
    city: typed?.city ?? "",
    site: typed?.site ?? "",
  };
  if (view === "confirm") return <ConfirmView typed={t} chosen={chosen} />;
  if (view === "checking") return <CheckingView />;
  if (view === "not-found") return <NotFoundView />;
  return <FindView results={view === "results"} typed={given} listings={listings} error={error} />;
}

function query(t: Typed, view: string): string {
  const q = new URLSearchParams({ view, name: t.name, city: t.city });
  if (t.site) q.set("site", t.site);
  return `/audit?${q.toString()}`;
}

function FindView({
  results,
  typed,
  listings,
  error,
}: {
  results: boolean;
  typed: Typed;
  listings?: Listing[];
  error?: string;
}) {
  const live = listings !== undefined;
  const matched = (listings ?? []).filter((li) => li.name_match).length;
  // The town steers the suggestions, so the field holding it is the one asked.
  const [city, setCity] = useState(typed.city);
  const [site, setSite] = useState(typed.site);
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
            <NameField
              defaultValue={typed.name}
              city={city}
              site={site}
              /* Examples only, and only before a search: once the button has been
                 pressed, an empty field stays plainly empty. */
              placeholder={results ? "" : "Alpha Plumbing"}
            />
            <Field label="City or town">
              {(id) => (
                <Input
                  id={id}
                  name="city"
                  value={city}
                  onChange={(e) => setCity(e.target.value)}
                  placeholder={results ? "" : "Mississauga, Ontario"}
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
                value={site}
                onChange={(e) => setSite(e.target.value)}
                placeholder={results ? "" : "alphaplumbing.ca"}
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

      {error ? (
        <Card className="border-red-line bg-red-pale mt-6 p-5">
          <p className="text-red text-[15px] leading-5 font-semibold">{error}</p>
          <p className="text-muted mt-2 text-[14px] leading-[18px]">
            You can still get the website check.{" "}
            <Link href="/audit?view=not-found" className="text-brand font-semibold">
              Tell us the basics instead
            </Link>
            .
          </p>
        </Card>
      ) : null}

      {results && !error ? (
        live ? (
          <LiveMatches listings={listings ?? []} matched={matched} typed={typed} />
        ) : (
          <SampleMatches typed={SAMPLE} />
        )
      ) : null}
    </AuditPage>
  );
}

function LiveMatches({
  listings,
  matched,
  typed,
}: {
  listings: Listing[];
  matched: number;
  typed: Typed;
}) {
  if (listings.length === 0) {
    return (
      <Card className="mt-6 p-5 sm:p-7">
        <p className="text-[16px] leading-5 font-semibold">
          Google has no listing under that name near {typed.city || "you"}.
        </p>
        <p className="text-muted mt-2 text-[15px] leading-[19px]">
          That is common for newer businesses, and it is worth fixing on its own. Tell us the basics
          and we will check your website anyway.
        </p>
        <div className="mt-4">
          <LinkButton href="/audit?view=not-found" size="sm">
            Check my website instead
          </LinkButton>
        </div>
      </Card>
    );
  }
  const heading =
    matched === 1
      ? "One business matches that name. Is it yours?"
      : matched > 1
        ? `${matched} businesses match that name. Which one is yours?`
        : "Nothing matches that name exactly. These are the nearest.";
  return (
    <form action="/audit" method="get" className="mt-6">
      <input type="hidden" name="view" value="confirm" />
      <input type="hidden" name="name" value={typed.name} />
      <input type="hidden" name="city" value={typed.city} />
      {typed.site ? <input type="hidden" name="site" value={typed.site} /> : null}
      <p className="text-muted text-[15px] leading-[18px] font-semibold">{heading}</p>
      <div className="mt-3 flex flex-col gap-3">
        {listings.map((li, i) => (
          <Result
            key={li.place_id}
            value={li.place_id}
            selected={i === 0}
            name={li.name}
            meta={listingMeta(li)}
            chip={listingRating(li)}
          />
        ))}
      </div>
      <div className="mt-5 flex flex-wrap items-center justify-between gap-4">
        <Link
          href="/audit?view=not-found"
          className="text-brand text-[14px] leading-[17px] font-semibold"
        >
          None of these are us
        </Link>
        <Button type="submit" size="sm" className="h-[42px]">
          This one
        </Button>
      </div>
      <p className="text-faint mt-4 text-[13px] leading-4">Business details from Google Maps.</p>
    </form>
  );
}

function SampleMatches({ typed }: { typed: Typed }) {
  return (
    <div className="mt-6">
      <p className="text-muted text-[15px] leading-[18px] font-semibold">
        Three businesses match. Which one is yours?
      </p>
      <div className="mt-3 flex flex-col gap-3">
        {SAMPLE_MATCHES.map((m, i) => (
          <Result key={m.name} value={m.name} selected={i === 0} {...m} />
        ))}
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
  );
}

function Result({
  name,
  meta,
  chip,
  selected,
  value,
}: {
  name: string;
  meta: string;
  chip: string;
  selected?: boolean;
  value: string;
}) {
  return (
    <label className="group border-line bg-panel hover:bg-line-soft has-checked:border-brand has-checked:bg-brand-tint flex cursor-pointer items-center gap-4 rounded-[12px] border px-4 py-4">
      <input
        type="radio"
        name="place"
        value={value}
        defaultChecked={selected}
        className="peer sr-only"
      />
      <span
        aria-hidden
        className="border-line-input peer-checked:border-brand flex size-[18px] shrink-0 items-center justify-center rounded-full border"
      >
        <span className="bg-brand hidden size-[9px] rounded-full group-has-checked:block" />
      </span>
      <span className="min-w-0 flex-1">
        <span className="text-ink block text-[16px] leading-[19px] font-semibold">{name}</span>
        <span className="text-faint mt-1 block text-[13px] leading-4">{meta}</span>
      </span>
      <Pill tone="grey">{chip}</Pill>
    </label>
  );
}

function ConfirmView({ typed, chosen }: { typed: Typed; chosen?: Listing }) {
  const name = chosen?.name ?? "Alpha Plumbing";
  const meta = chosen
    ? listingMeta(chosen)
    : "Plumber · 1420 Dundas Street East, Mississauga, Ontario";
  const rating = chosen ? listingRating(chosen) : "4.6 · 87 reviews";
  const site = typed.site || chosen?.website?.replace(/^https?:\/\//, "").replace(/\/$/, "") || "";
  return (
    <AuditPage>
      <h1 className="text-[32px] leading-[38px] font-bold sm:text-[42px] sm:leading-[51px]">
        Is this you?
      </h1>
      <p className="text-muted mt-6 max-w-[700px] text-[18px] leading-[22px]">
        This is what Google shows about you today. If something looks wrong here, it looks wrong to
        your customers too.
      </p>
      <Card className="mt-6">
        <div className="flex flex-col gap-5 p-5 sm:p-7">
          <div className="min-w-0">
            <span className="text-[24px] leading-[29px] font-bold">{name}</span>
            <p className="text-muted mt-[10px] text-[15px] leading-[18px]">{meta}</p>
            <p className="text-muted mt-[10px] text-[15px] leading-[18px]">
              {rating}
              {site ? ` · ${site}` : ""}
              {chosen?.phone ? ` · ${chosen.phone}` : ""}
            </p>
            {chosen ? (
              <p className="text-faint mt-[10px] text-[13px] leading-4">
                From Google Maps.{" "}
                {chosen.maps_url ? (
                  <Link href={chosen.maps_url} className="text-brand font-semibold">
                    See the listing
                  </Link>
                ) : null}
              </p>
            ) : null}
          </div>
        </div>
        <div className="border-line-soft flex flex-col gap-3 border-t px-5 py-5 sm:flex-row sm:items-center sm:justify-between sm:px-7">
          <Link
            href={query(typed, "results")}
            className="text-muted text-[14px] leading-[17px] font-semibold"
          >
            Not us. Search again
          </Link>
          {site ? (
            <StartAudit
              business={chosen?.name ?? typed.name}
              city={typed.city}
              site={site}
              placeId={chosen?.place_id ?? ""}
              label="Yes, that is us. Check it"
            />
          ) : (
            /* Google has no website for them and none was typed, so there is
               nothing to check yet. The manual form is the one place that asks. */
            <LinkButton href={query(typed, "not-found")} size="sm" className="h-[42px]">
              Yes. Add my website
            </LinkButton>
          )}
        </div>
      </Card>
      {site ? null : (
        <p className="text-muted mt-4 text-[15px] leading-[19px]">
          Google has no website on this listing. That is worth fixing on its own, and we need the
          address to check the page your ads would send people to.
        </p>
      )}
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
