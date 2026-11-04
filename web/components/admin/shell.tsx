"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import type { Whoami } from "@/lib/admin";
import { SignOut } from "./sign-out";

/*
  The panel's shell.

  The last version used the study's "no sidebar" archetype: a top bar over a
  centred column. That archetype is for reports, viewers and products with few
  destinations, and this product has seven. A tab row carrying seven
  destinations over an empty page is why the panel read as a web page rather
  than a tool, and why the content floated with three hundred pixels of dead
  ground under it.

  This is "tinted frame, white sheet", the commonest shell in the study: the
  sidebar and the top bar share the page's tinted ground with no rule between
  them, and the work sits on a white sheet inset from the window's right and
  bottom edges, radius 16, a 1px edge and no shadow. The ground is the app's
  own `--pw-ground`, which is already in that range, so this is the app's
  palette arranged the way a tool arranges it.

  Two measured things it also fixes. The product is named at the top of the
  sidebar, because a screen whose product cannot be named from a screenshot
  reads as a template. And counts appear only on destinations that need
  action, with the noun clear from the label: "Failures 3" says what three is.

  Not dark. No screen in the study puts a dark or saturated sidebar against a
  light canvas, and the previous dark band across the top was exactly that.
  The staff warning keeps its weight by sitting in the top bar in the warning
  colour, where it is read before anything else, rather than by inverting a
  whole strip of chrome.
*/

type Item = { href: string; label: string; needs: string; count?: number };

/*
  Declared here rather than inside `Shell`. A component created during render
  is a new type on every render, so React throws its state away each time --
  which for a drawer means it closes itself as you touch it.
*/
function Group({
  title,
  items,
  here,
  may,
  onGo,
}: {
  title: string;
  items: Item[];
  here: string;
  may: string[];
  onGo: () => void;
}) {
  const shown = items.filter((one) => may.includes(one.needs));
  if (!shown.length) return null;
  return (
    <div className="mt-6 first:mt-0">
      {/* Sentence case, never uppercase: 9 of the 16 studied sidebars. */}
      <p className="text-pw-ink-400 px-3 pb-2 text-[12px] leading-[16px]">{title}</p>
      <ul>
        {shown.map((one) => {
          const current = here === one.href;
          return (
            <li key={one.href}>
              <Link
                href={one.href}
                onClick={onGo}
                aria-current={current ? "page" : undefined}
                className={[
                  "flex h-8 items-center justify-between gap-2 rounded-[8px] px-3 text-[14px] leading-[20px] transition-colors",
                  current
                    ? "bg-pw-border-strong/45 text-pw-ink font-medium"
                    : "text-pw-ink-600 hover:bg-pw-border/50 hover:text-pw-ink",
                ].join(" ")}
              >
                <span className="truncate">{one.label}</span>
                {one.count ? (
                  <span className="pw-num text-pw-bad text-[12px] leading-[16px] font-medium">
                    {one.count}
                  </span>
                ) : null}
              </Link>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export function Shell({
  who,
  looking_at,
  counts,
  children,
}: {
  who: Whoami;
  looking_at?: string;
  counts?: { failures?: number; waiting?: number };
  children: React.ReactNode;
}) {
  const here = usePathname();
  const [open, setOpen] = useState(false);

  const work: Item[] = [
    { href: "/admin", label: "Merchants", needs: "read_merchant" },
    { href: "/admin/metrics", label: "Overview", needs: "read_platform", count: counts?.waiting },
  ];
  const health: Item[] = [
    { href: "/admin/jobs", label: "Jobs", needs: "run_job" },
    { href: "/admin/errors", label: "Failures", needs: "read_errors", count: counts?.failures },
    { href: "/admin/quota", label: "Quota", needs: "read_platform" },
  ];
  const control: Item[] = [
    { href: "/admin/platform", label: "Settings", needs: "read_platform" },
    { href: "/admin/staff", label: "Access", needs: "grant_staff" },
  ];

  const sidebar = (
    <>
      <div className="flex items-center gap-2 px-3 pb-5">
        <span
          aria-hidden
          className="bg-pw-blue flex h-6 w-6 shrink-0 items-center justify-center rounded-[7px] text-[12px] leading-none font-bold text-white"
        >
          P
        </span>
        <span className="text-pw-ink min-w-0 truncate text-[14px] leading-[20px] font-semibold">
          PPCWay
        </span>
        <span className="text-pw-ink-400 shrink-0 text-[12px] leading-[16px]">internal</span>
      </div>
      <nav aria-label="Internal panel" className="flex-1">
        <Group
          title="Customers"
          items={work}
          here={here}
          may={who.may}
          onGo={() => setOpen(false)}
        />
        <Group
          title="Running"
          items={health}
          here={here}
          may={who.may}
          onGo={() => setOpen(false)}
        />
        <Group
          title="Control"
          items={control}
          here={here}
          may={who.may}
          onGo={() => setOpen(false)}
        />
      </nav>
      {/* The user row the study puts at the bottom of 8 of 23 sidebars. */}
      <div className="border-pw-border mt-6 border-t px-3 pt-3">
        <p className="text-pw-ink truncate text-[13px] leading-[18px] font-medium">
          {who.who ?? "Signed in"}
        </p>
        <p className="text-pw-ink-400 text-[12px] leading-[16px]">{who.level} access</p>
        <p className="mt-2 flex items-center gap-3 text-[13px] leading-[18px]">
          <Link
            href="/home"
            className="text-pw-ink-600 hover:text-pw-ink underline underline-offset-2"
          >
            Your dashboard
          </Link>
          <SignOut />
        </p>
      </div>
    </>
  );

  return (
    <div className="bg-pw-ground min-h-[100dvh] lg:flex">
      {/* Desktop sidebar: 232px, the study's median of 230. */}
      <aside className="hidden w-[232px] shrink-0 flex-col px-3 py-5 lg:flex">{sidebar}</aside>

      {/* Phone and tablet: the same sidebar as a drawer, because seven
          destinations do not fit across a handset and a scrolling tab row
          hides the last three. */}
      {open ? (
        <>
          <button
            aria-label="Close the menu"
            onClick={() => setOpen(false)}
            className="bg-pw-ink/30 fixed inset-0 z-50 lg:hidden"
          />
          <aside className="bg-pw-ground fixed inset-y-0 left-0 z-50 flex w-[260px] flex-col overflow-y-auto px-3 py-5 lg:hidden">
            {sidebar}
          </aside>
        </>
      ) : null}

      <div className="flex min-w-0 flex-1 flex-col">
        {/* The top bar holds something real: who you are looking at, and the
            way to the menu on a small screen. */}
        <header className="flex h-12 shrink-0 items-center gap-3 px-4 lg:pr-4 lg:pl-0">
          <button
            onClick={() => setOpen(true)}
            className="text-pw-ink-600 hover:text-pw-ink -ml-1 flex h-8 w-8 items-center justify-center rounded-[8px] lg:hidden"
            aria-label="Open the menu"
          >
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden>
              <path
                d="M2.5 4.5h13M2.5 9h13M2.5 13.5h13"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
              />
            </svg>
          </button>
          <span className="text-pw-ink text-[14px] leading-[20px] font-semibold lg:hidden">
            PPCWay internal
          </span>

          {looking_at ? (
            <p className="text-pw-warn-ink bg-pw-warn-bg border-pw-warn-border ml-auto truncate rounded-[8px] border px-2.5 py-1 text-[13px] leading-[18px] font-medium">
              You are in {looking_at}&rsquo;s account, not your own
            </p>
          ) : (
            <p className="text-pw-ink-400 ml-auto hidden truncate text-[12px] leading-[16px] lg:block">
              Every account you open is recorded
            </p>
          )}
        </header>

        {/* The white sheet, inset from the window's right and bottom edges. */}
        <div className="border-pw-border min-w-0 flex-1 overflow-hidden rounded-tl-[16px] border-t border-l bg-white max-lg:rounded-tr-[16px] max-lg:border-r lg:mr-2 lg:mb-2 lg:rounded-[16px] lg:border">
          {children}
        </div>
      </div>
    </div>
  );
}
