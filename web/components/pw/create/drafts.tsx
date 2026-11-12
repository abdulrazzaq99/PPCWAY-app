"use client";

import { ArrowRightIcon, NotePencilIcon, TrashIcon } from "@phosphor-icons/react";
import Link from "next/link";
import { useState } from "react";
import { cn } from "@/lib/cn";

/*
  Campaigns started and not yet published, in a narrow panel beside the
  campaign list rather than across the top of the page: Google keeps drafts
  where they can be picked up, but they are not what a merchant opens the
  Campaigns page to read. The first few show; the rest are a click away, and
  a draft nobody wants can be removed here (a published campaign never can).
*/
export type DraftRow = {
  id: string;
  name: string;
  type: string;
  v: number;
  created_at: string | null;
};

const TYPE: Record<string, string> = {
  SEARCH: "Search",
  PERFORMANCE_MAX: "Performance Max",
  DEMAND_GEN: "Demand Gen",
  DISPLAY: "Display",
  SHOPPING: "Shopping",
  APP: "App",
};

/** How many drafts show before "Show all": six in the grid under the list
 * (two rows of three), four in the narrow panel beside it. */
const FIRST = 6;
const FIRST_BESIDE = 4;

function started(iso: string | null): string {
  if (!iso) return "";
  const then = new Date(iso.endsWith("Z") || iso.includes("+") ? iso : `${iso}Z`);
  const days = Math.floor((Date.now() - then.getTime()) / 86_400_000);
  if (days <= 0) return "started today";
  if (days === 1) return "started yesterday";
  return `started ${then.toLocaleDateString(undefined, { month: "short", day: "numeric" })}`;
}

export function Drafts({ drafts: initial }: { drafts: DraftRow[] }) {
  const [drafts, setDrafts] = useState(initial);
  const [all, setAll] = useState(false);
  const [asking, setAsking] = useState("");
  const [busy, setBusy] = useState("");
  const [trouble, setTrouble] = useState("");

  if (!drafts.length) return null;
  const shown = all ? drafts : drafts.slice(0, FIRST);

  async function remove(id: string) {
    setBusy(id);
    setTrouble("");
    const res = await fetch(`/api/campaigns/v2/${id}/discard`, { method: "POST", body: "{}" });
    setBusy("");
    setAsking("");
    if (!res.ok) {
      const said = (await res.json().catch(() => ({}))) as { error?: string };
      setTrouble(said.error ?? "That draft could not be removed.");
      return;
    }
    setDrafts((list) => list.filter((d) => d.id !== id));
  }

  return (
    <section aria-labelledby="drafts-heading" className="flex flex-col gap-3">
      {/* The same height as the list's own heading row, so both cards start level. */}
      <header className="flex min-h-[42px] items-center justify-between gap-3">
        <h2 id="drafts-heading" className="text-[17px] leading-[22px] font-semibold">
          Drafts <span className="text-pw-ink-400 font-normal">{drafts.length}</span>
        </h2>
        <p className="text-pw-ink-500 text-[12px]">Not live until published</p>
      </header>
      <div className="bg-pw-card border-pw-border overflow-hidden rounded-[18px] border">
        {/* Hairlines from a 1px gap over the border colour, so the dividers stay
            clean whether the drafts are one column, two or three. */}
        <ul className="bg-pw-border grid gap-px sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-1">
          {shown.map((d, at) => (
            <li
              key={d.id}
              className={cn(
                "group bg-pw-card relative",
                !all && at >= FIRST_BESIDE && "2xl:hidden",
              )}
            >
              {asking === d.id ? (
                <div className="flex items-center justify-between gap-2 px-5 py-3 text-[13px]">
                  <span className="text-pw-ink-700 min-w-0 truncate">
                    Remove <span className="font-semibold">{d.name}</span>?
                  </span>
                  <span className="flex shrink-0 items-center gap-1">
                    <button
                      type="button"
                      onClick={() => remove(d.id)}
                      disabled={busy === d.id}
                      className="text-pw-bad hover:bg-pw-bad-bg rounded-full px-3 py-1 font-semibold"
                    >
                      {busy === d.id ? "Removing…" : "Remove"}
                    </button>
                    <button
                      type="button"
                      onClick={() => setAsking("")}
                      className="text-pw-ink-600 hover:bg-pw-muted rounded-full px-3 py-1 font-semibold"
                    >
                      Keep
                    </button>
                  </span>
                </div>
              ) : (
                <div className="flex items-center">
                  <Link
                    href={`/campaigns/new/${d.id}`}
                    className="hover:bg-pw-row-hover flex min-w-0 flex-1 items-center gap-3 py-3 pr-2 pl-5"
                  >
                    <NotePencilIcon className="text-pw-ink-400 size-[18px] shrink-0" aria-hidden />
                    <span className="min-w-0 flex-1">
                      <span className="text-pw-ink block truncate text-[14px] font-medium">
                        {d.name || "Untitled campaign"}
                      </span>
                      <span className="text-pw-ink-500 block truncate text-[12px]">
                        {TYPE[d.type] ?? d.type}
                        {started(d.created_at) ? `, ${started(d.created_at)}` : ""}
                      </span>
                    </span>
                    <ArrowRightIcon
                      className="text-pw-blue size-4 shrink-0 transition-transform group-hover:translate-x-0.5"
                      aria-label="Continue"
                    />
                  </Link>
                  <button
                    type="button"
                    onClick={() => setAsking(d.id)}
                    aria-label={`Remove the draft ${d.name}`}
                    className={cn(
                      "text-pw-ink-300 hover:text-pw-bad mr-3 rounded-full p-2 transition-opacity",
                      "opacity-100 sm:opacity-0 sm:group-hover:opacity-100 sm:focus-visible:opacity-100",
                    )}
                  >
                    <TrashIcon className="size-4" />
                  </button>
                </div>
              )}
            </li>
          ))}
        </ul>
        {trouble ? <p className="text-pw-bad px-5 py-2 text-[13px]">{trouble}</p> : null}
        {drafts.length > FIRST_BESIDE ? (
          <button
            type="button"
            onClick={() => setAll((a) => !a)}
            className={cn(
              "text-pw-blue hover:bg-pw-row-hover border-pw-border w-full border-t px-5 py-3 text-left text-[13px] font-semibold",
              // Up to six fit the grid, so the button is only needed beside the list.
              !all && drafts.length <= FIRST && "hidden 2xl:block",
            )}
          >
            {all ? "Show fewer" : `Show all ${drafts.length}`}
          </button>
        ) : null}
      </div>
    </section>
  );
}
