"use client";

import { ListIcon, XIcon } from "@phosphor-icons/react";
import { useEffect, useState, type ReactNode } from "react";

/*
  The navigation on a phone or a tablet: a menu button in the top bar that
  opens the whole sidebar as a full-screen sheet. Seven destinations do not
  fit across a handset, and a tab row that scrolls sideways hides the last
  three.

  The sheet's contents are rendered on the server and handed in, so the
  links, the search and the sign-out are the same ones the desktop sidebar
  shows. It closes when a link is followed, and on Escape.
*/
export function PhoneMenu({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("keydown", onKey);
    const was = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = was;
    };
  }, [open]);

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-label="Open the menu"
        aria-expanded={open}
        className="text-ad-muted hover:text-ad-text -ml-2 flex h-10 w-10 items-center justify-center rounded-full lg:hidden"
      >
        <ListIcon size={20} aria-hidden />
      </button>
      {open ? (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="Menu"
          className="bg-ad-ground fixed inset-0 z-50 flex flex-col overflow-y-auto lg:hidden"
          onClick={(event) => {
            if ((event.target as HTMLElement).closest("a")) setOpen(false);
          }}
        >
          <div className="border-ad-border flex h-14 flex-none items-center justify-end border-b px-4">
            <button
              type="button"
              onClick={() => setOpen(false)}
              aria-label="Close the menu"
              className="text-ad-muted hover:text-ad-text flex h-10 w-10 items-center justify-center rounded-full"
            >
              <XIcon size={20} aria-hidden />
            </button>
          </div>
          {children}
        </div>
      ) : null}
    </>
  );
}
