"use client";

import { useEffect, useId, useRef, useState } from "react";
import { BOX, fieldBorder } from "@/components/audit/funnel/bits";
import { cn } from "@/lib/cn";
import type { Listing } from "@/lib/listing";
import { listingMeta, listingRating } from "@/lib/listing";

/*
  The business name, with Google's own listings arriving as it is typed.

  This is not a convenience. Picking a listing hands us its place id, which is
  the difference between knowing which business this is and inferring it from a
  website address. "Alpha Plumbing" returns four businesses on Google, two of
  them with that exact name; guessing between them is how one company gets
  another's audit. Picking removes the guess.

  Typing a name Google has never heard of still works: the field is a plain
  text box underneath, and nothing here has to be used.
*/
const WAIT_MS = 420;
const ENOUGH = 3;

export function NameSuggest({
  value,
  onChange,
  onPick,
  invalid,
}: {
  value: string;
  onChange: (text: string) => void;
  onPick: (listing: Listing) => void;
  invalid?: boolean;
}) {
  const listId = useId();
  const [list, setList] = useState<Listing[]>([]);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const box = useRef<HTMLDivElement>(null);
  // What they last chose, so a reply that arrives late cannot reopen the list
  // underneath a decision already made.
  const settled = useRef(false);
  // Answers already paid for. Each search is a billed call, so backspacing
  // over a word should not buy the same answer twice.
  const answered = useRef(new Map<string, Listing[]>());

  useEffect(() => {
    const ask = value.trim();
    if (settled.current || ask.length < ENOUGH) {
      setList([]);
      setOpen(false);
      return;
    }
    const remembered = answered.current.get(ask);
    if (remembered) {
      setList(remembered);
      setOpen(remembered.length > 0);
      setActive(-1);
      return;
    }
    const stop = new AbortController();
    const wait = window.setTimeout(async () => {
      try {
        const res = await fetch(`/api/places/suggest?q=${encodeURIComponent(ask)}`, {
          signal: stop.signal,
          cache: "no-store",
        });
        const found = (await res.json()) as Listing[];
        if (Array.isArray(found)) {
          answered.current.set(ask, found);
          setList(found);
          setOpen(found.length > 0);
          setActive(-1);
        }
      } catch {
        /* no suggestions is not an error worth showing anybody */
      }
    }, WAIT_MS);
    return () => {
      window.clearTimeout(wait);
      stop.abort();
    };
  }, [value]);

  useEffect(() => {
    function away(event: MouseEvent) {
      if (box.current && !box.current.contains(event.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", away);
    return () => document.removeEventListener("mousedown", away);
  }, []);

  function choose(pick: Listing) {
    settled.current = true;
    setOpen(false);
    onPick(pick);
  }

  function onKey(event: React.KeyboardEvent<HTMLInputElement>) {
    if (!open || !list.length) return;
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActive((at) => (at + 1) % list.length);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActive((at) => (at <= 0 ? list.length - 1 : at - 1));
    } else if (event.key === "Enter" && active >= 0) {
      event.preventDefault();
      choose(list[active]);
    } else if (event.key === "Escape") {
      setOpen(false);
    }
  }

  return (
    <div ref={box} className="relative">
      <input
        id="biz"
        type="text"
        autoComplete="organization"
        placeholder="Your business or brand"
        value={value}
        role="combobox"
        aria-expanded={open}
        aria-controls={listId}
        aria-autocomplete="list"
        aria-activedescendant={active >= 0 && list[active] ? `${listId}-${active}` : undefined}
        onChange={(e) => {
          settled.current = false;
          onChange(e.target.value);
        }}
        onFocus={() => setOpen(list.length > 0)}
        onKeyDown={onKey}
        className={cn(BOX, fieldBorder(invalid), "font-normal")}
      />
      {open && list.length > 0 && (
        <ul
          id={listId}
          role="listbox"
          className="border-line absolute z-20 mt-1 max-h-[280px] w-full overflow-auto rounded-[12px] border bg-white py-1 shadow-[0_20px_50px_-20px_rgba(21,17,42,0.3)]"
        >
          {list.map((one, at) => (
            <li
              key={one.place_id}
              id={`${listId}-${at}`}
              role="option"
              aria-selected={at === active}
            >
              <button
                type="button"
                onMouseEnter={() => setActive(at)}
                onClick={() => choose(one)}
                className={cn(
                  "flex w-full flex-col items-start gap-[2px] px-4 py-[10px] text-left",
                  at === active ? "bg-[#EEF2FE]" : "bg-white",
                )}
              >
                <span className="text-[15px] leading-[19px] font-semibold">{one.name}</span>
                <span className="text-[13px] leading-[17px] text-[#6B6680]">
                  {[listingMeta(one), listingRating(one)].filter(Boolean).join(" · ")}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
