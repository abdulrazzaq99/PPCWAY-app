"use client";

import { MagnifyingGlassIcon } from "@phosphor-icons/react";
import { useEffect, useRef } from "react";

/*
  Finding a business, from anywhere in the console.

  The commonest thing a member of staff does here is look somebody up, so the
  search lives in the top bar on every screen rather than only on the list.
  It is a plain GET form to the merchant list, so it works before any script
  has loaded; the script adds only the "/" key, the way most consoles let you
  start typing without reaching for the mouse.
*/
export function Search({
  id,
  defaultValue = "",
  shortcut = false,
  wide = false,
}: {
  id: string;
  defaultValue?: string;
  /* Only one instance on a screen answers the key. */
  shortcut?: boolean;
  wide?: boolean;
}) {
  const box = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!shortcut) return;
    function onKey(event: KeyboardEvent) {
      const target = event.target as HTMLElement | null;
      const typing = target?.closest("input, textarea, select, [contenteditable='true']");
      if (event.key === "/" && !typing && !event.metaKey && !event.ctrlKey) {
        event.preventDefault();
        box.current?.focus();
        box.current?.select();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [shortcut]);

  return (
    <form
      action="/admin"
      role="search"
      className={`border-ad-control focus-within:border-ad-accent relative flex h-[34px] items-center rounded-full border transition-colors ${
        wide ? "w-full" : "w-[300px]"
      }`}
    >
      <label htmlFor={id} className="sr-only">
        Find a business by name
      </label>
      <MagnifyingGlassIcon
        aria-hidden
        size={15}
        className="text-ad-faint pointer-events-none absolute left-3.5"
      />
      <input
        ref={box}
        id={id}
        name="q"
        type="search"
        defaultValue={defaultValue}
        placeholder="Find a business"
        autoComplete="off"
        className="text-ad-text placeholder:text-ad-faint h-full w-full rounded-full bg-transparent pr-10 pl-9 text-[13px] outline-none [&::-webkit-search-cancel-button]:hidden"
      />
      {shortcut ? (
        <kbd
          aria-hidden
          className="border-ad-control text-ad-faint ad-num absolute right-2.5 flex h-5 min-w-5 items-center justify-center rounded-[4px] border px-1 text-[11px]"
        >
          /
        </kbd>
      ) : null}
    </form>
  );
}
