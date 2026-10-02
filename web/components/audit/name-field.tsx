"use client";

import { useRouter } from "next/navigation";
import { useEffect, useId, useRef, useState } from "react";
import { Field, Input } from "@/components/ui/field";
import type { Listing } from "@/lib/listing";
import { listingMeta, listingRating } from "@/lib/listing";

/*
  The business name, with Google's suggestions arriving as it is typed. Picking
  one goes straight to the listing, skipping the matches screen; typing a name
  Google does not know still works, because the button below is untouched.

  The list is the same search the button runs, so what appears while typing is
  what pressing the button would find.
*/

export function NameField({
  defaultValue,
  city,
  site,
  placeholder,
}: {
  defaultValue: string;
  city: string;
  site: string;
  placeholder?: string;
}) {
  const router = useRouter();
  const listId = useId();
  const [typed, setTyped] = useState(defaultValue);
  const [list, setList] = useState<Listing[]>([]);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const box = useRef<HTMLDivElement>(null);
  // What the person last chose or typed, so a stale reply cannot reopen the list.
  const settled = useRef(false);
  // Answers already paid for, so backspacing costs nothing.
  const answered = useRef(new Map<string, Listing[]>());

  useEffect(() => {
    const ask = typed.trim();
    // Three letters, not two: two matches half the businesses in a town and costs
    // a search either way. Each search is a paid call, so they are not spent on
    // a query nobody could answer usefully.
    if (settled.current || ask.length < 3) {
      setList([]);
      return;
    }
    const remembered = answered.current.get(`${ask}|${city}`);
    if (remembered) {
      setList(remembered);
      setOpen(remembered.length > 0);
      setActive(-1);
      return;
    }
    const stop = new AbortController();
    const wait = window.setTimeout(async () => {
      try {
        const query = new URLSearchParams({ q: ask, city });
        const res = await fetch(`/api/places/suggest?${query}`, {
          signal: stop.signal,
          cache: "no-store",
        });
        const found = (await res.json()) as Listing[];
        if (Array.isArray(found)) {
          answered.current.set(`${ask}|${city}`, found);
          setList(found);
          setOpen(found.length > 0);
          setActive(-1);
        }
      } catch {
        /* a missing suggestion list is not an error worth showing */
      }
      // Longer than it feels: a pause of this length turns a typed name into two or
      // three searches rather than one per letter.
    }, 420);
    return () => {
      window.clearTimeout(wait);
      stop.abort();
    };
  }, [typed, city]);

  useEffect(() => {
    function away(event: MouseEvent) {
      if (box.current && !box.current.contains(event.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", away);
    return () => document.removeEventListener("mousedown", away);
  }, []);

  function choose(pick: Listing) {
    settled.current = true;
    setTyped(pick.name);
    setOpen(false);
    const where = new URLSearchParams({ view: "confirm", place: pick.place_id, name: pick.name });
    if (city) where.set("city", city);
    if (site) where.set("site", site);
    router.push(`/audit?${where}`);
  }

  function onKey(event: React.KeyboardEvent<HTMLInputElement>) {
    if (!open || list.length === 0) return;
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      const step = event.key === "ArrowDown" ? 1 : -1;
      setActive((was) => (was + step + list.length) % list.length);
    } else if (event.key === "Enter" && active >= 0) {
      event.preventDefault();
      choose(list[active]);
    } else if (event.key === "Escape") {
      setOpen(false);
    }
  }

  return (
    <div ref={box} className="relative">
      <Field label="Business name">
        {(id) => (
          <Input
            id={id}
            name="name"
            value={typed}
            placeholder={placeholder}
            autoComplete="off"
            role="combobox"
            aria-expanded={open}
            aria-controls={listId}
            aria-autocomplete="list"
            aria-activedescendant={active >= 0 ? `${listId}-${active}` : undefined}
            onChange={(e) => {
              settled.current = false;
              setTyped(e.target.value);
            }}
            onFocus={() => setOpen(list.length > 0)}
            onKeyDown={onKey}
          />
        )}
      </Field>
      {open && list.length > 0 ? (
        <ul
          id={listId}
          role="listbox"
          aria-label="Businesses Google knows"
          className="border-line bg-panel absolute top-full right-0 left-0 z-20 mt-1 overflow-hidden rounded-[12px] border shadow-[0_18px_40px_-20px_rgba(15,23,32,0.45)]"
        >
          {list.map((pick, i) => (
            <li
              key={pick.place_id}
              id={`${listId}-${i}`}
              role="option"
              aria-selected={i === active}
            >
              <button
                type="button"
                onMouseEnter={() => setActive(i)}
                onClick={() => choose(pick)}
                className={`block w-full px-4 py-3 text-left ${i === active ? "bg-brand-tint" : "hover:bg-line-soft"}`}
              >
                <span className="flex items-center justify-between gap-3">
                  <span className="text-ink text-[15px] leading-[19px] font-semibold">
                    {pick.name}
                  </span>
                  <span className="text-faint shrink-0 text-[12px] leading-4">
                    {listingRating(pick)}
                  </span>
                </span>
                <span className="text-faint mt-[2px] block text-[13px] leading-4">
                  {listingMeta(pick)}
                </span>
              </button>
            </li>
          ))}
          <li className="text-faint border-line-soft border-t px-4 py-2 text-[12px] leading-4">
            Businesses from Google Maps
          </li>
        </ul>
      ) : null}
    </div>
  );
}
