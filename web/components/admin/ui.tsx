import { CaretLeftIcon, CaretRightIcon } from "@phosphor-icons/react/dist/ssr";
import Link from "next/link";
import type { CSSProperties, ReactNode } from "react";
import { count, initials, tintOf } from "@/lib/admin";

/*
  The console's parts. Every screen is built from these, so the rules are
  written once:

  - Panels are 6px with a 1px edge a whisper lighter than the ground. No
    shadow on anything at rest.
  - Every selection is the same mark: one 1px line in the accent, exactly as
    wide as the label it marks, sitting on the nearest edge that already
    exists. Tabs, the sidebar, a chosen window. Never a filled pill.
  - Colour goes on data and status. Chrome stays grey.
  - Figures are mono (`.ad-num`), right-aligned in columns, with a sign on
    every change.
*/

/* ---------- the page head ---------- */

export function Head({
  title,
  pill,
  lead,
  side,
}: {
  title: string;
  pill?: ReactNode;
  lead?: ReactNode;
  side?: ReactNode;
}) {
  return (
    <header className="flex flex-wrap items-start justify-between gap-x-6 gap-y-4">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
          <h1 className="text-[22px] leading-[28px] font-semibold tracking-[-0.01em] sm:text-[26px] sm:leading-[32px]">
            {title}
          </h1>
          {pill}
        </div>
        {lead ? (
          <p className="text-ad-muted mt-1.5 max-w-[78ch] text-[13px] leading-[20px]">{lead}</p>
        ) : null}
      </div>
      {side ? <div className="flex shrink-0 flex-wrap items-center gap-2">{side}</div> : null}
    </header>
  );
}

/* ---------- tabs: the style's one move ---------- */

export type Tab = { label: string; href: string; count?: number; here: boolean };

export function Tabs({ tabs, label }: { tabs: Tab[]; label: string }) {
  return (
    <nav aria-label={label} className="border-ad-border -mx-4 border-b px-4 sm:mx-0 sm:px-0">
      <ul className="-mb-px flex [scrollbar-width:none] gap-6 overflow-x-auto">
        {tabs.map((one) => (
          <li key={one.href} className="shrink-0">
            <Link
              href={one.href}
              aria-current={one.here ? "page" : undefined}
              className={[
                "relative inline-flex h-10 items-center gap-2 text-[13px] transition-colors duration-150",
                one.here ? "text-ad-text font-medium" : "text-ad-faint hover:text-ad-text",
              ].join(" ")}
            >
              <span className="relative">
                {one.label}
                {/* The 1px accent line, as wide as the label, on the rule. */}
                {one.here ? (
                  <span
                    aria-hidden
                    className="bg-ad-accent absolute right-0 -bottom-[11px] left-0 h-px"
                  />
                ) : null}
              </span>
              {one.count !== undefined ? (
                <span className="ad-num text-ad-faint text-[12px]">{one.count}</span>
              ) : null}
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}

/* ---------- panels ---------- */

export function Panel({
  title,
  meta,
  action,
  children,
  className = "",
  flush = false,
  grow = false,
  id,
}: {
  title?: ReactNode;
  meta?: ReactNode;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
  /* Content runs to the panel's edges: a table, a feed. */
  flush?: boolean;
  /* The body fills the panel's height, for a chart that takes the row's height. */
  grow?: boolean;
  id?: string;
}) {
  return (
    <section
      id={id}
      className={`border-ad-border bg-ad-surface min-w-0 rounded-[6px] border ${
        grow ? "flex flex-col" : ""
      } ${className}`}
    >
      {title || meta || action ? (
        <header className="flex flex-wrap items-start justify-between gap-x-4 gap-y-1 px-5 pt-4">
          <div className="min-w-0">
            {title ? <h2 className="text-[15px] leading-[22px] font-semibold">{title}</h2> : null}
            {meta ? (
              <div className="text-ad-faint mt-0.5 text-[13px] leading-[20px]">{meta}</div>
            ) : null}
          </div>
          {action ? <div className="shrink-0 text-[13px] leading-[22px]">{action}</div> : null}
        </header>
      ) : null}
      <div
        className={`${flush ? "pt-3" : "px-5 pt-3 pb-5"} ${grow ? "flex min-h-0 flex-1 flex-col" : ""}`}
      >
        {children}
      </div>
    </section>
  );
}

/* A quiet link in a panel's header: "View all 14". */
export function More({ href, children }: { href: string; children: ReactNode }) {
  return (
    <Link
      href={href}
      className="text-ad-accent hover:text-ad-text text-[13px] leading-[22px] font-medium transition-colors"
    >
      {children}
    </Link>
  );
}

/* ---------- figures ---------- */

export type FigureCell = {
  label: string;
  value: string;
  unit?: string;
  note?: ReactNode;
  /* Colour on the note says good or bad for this figure, never up or down. */
  noteTone?: "plain" | "good" | "bad";
  /* The figure the screen's question turns on, set a step larger. */
  lead?: boolean;
  /* A count that needs action, in the negative colour. */
  alarm?: boolean;
  /* A count close to a limit, in the warning colour. */
  warn?: boolean;
  unknown?: boolean;
  href?: string;
};

export function Figures({ cells }: { cells: FigureCell[] }) {
  /*
    One container divided by 1px lines, never a card per figure. The column
    count is the item count, so four figures fill four columns and none is
    left orphaned in a grid made for three. On a phone, two columns, and an
    odd last cell takes the whole row.
  */
  const cols =
    cells.length >= 5
      ? "lg:grid-cols-5"
      : cells.length === 4
        ? "lg:grid-cols-4"
        : cells.length === 3
          ? "lg:grid-cols-3"
          : "lg:grid-cols-2";
  return (
    <dl
      className={`border-ad-border bg-ad-border grid grid-cols-2 gap-px overflow-hidden rounded-[6px] border ${cols}`}
    >
      {cells.map((one, at) => {
        const body = (
          <>
            <dt className="text-ad-muted text-[13px] leading-[20px]">{one.label}</dt>
            <dd
              className={[
                "ad-num mt-1.5",
                one.lead ? "text-[28px] leading-[34px]" : "text-[20px] leading-[28px]",
                one.unknown
                  ? "text-ad-faint"
                  : one.alarm
                    ? "text-ad-negative"
                    : one.warn
                      ? "text-ad-warning"
                      : "text-ad-text",
              ].join(" ")}
            >
              {one.unknown ? "Unknown" : one.value}
              {one.unit && !one.unknown ? (
                <span className="text-ad-faint ml-1 text-[12px]">{one.unit}</span>
              ) : null}
            </dd>
            {one.note ? (
              <dd
                className={`mt-1 text-[13px] leading-[20px] ${
                  one.noteTone === "bad"
                    ? "text-ad-negative"
                    : one.noteTone === "good"
                      ? "text-ad-positive"
                      : "text-ad-faint"
                }`}
              >
                {one.note}
              </dd>
            ) : null}
          </>
        );
        const odd = cells.length % 2 === 1 && at === cells.length - 1;
        const cell = `bg-ad-surface block px-5 py-4 ${odd ? "col-span-2 lg:col-span-1" : ""}`;
        return one.href ? (
          <Link
            key={one.label}
            href={one.href}
            className={`${cell} hover:bg-ad-raised transition-colors duration-150`}
          >
            {body}
          </Link>
        ) : (
          <div key={one.label} className={cell}>
            {body}
          </div>
        );
      })}
    </dl>
  );
}

/* ---------- marks ---------- */

export type Tone = "good" | "bad" | "warn" | "info" | "plain";

const PILL: Record<Tone, string> = {
  good: "bg-ad-positive-tint text-ad-positive-ink",
  bad: "bg-ad-negative-tint text-ad-negative",
  warn: "bg-ad-warning-tint text-ad-warning",
  info: "bg-ad-accent-tint text-ad-accent",
  plain: "bg-ad-neutral-tint text-ad-neutral-ink",
};

/* A state in a row or beside a title. One per row; never squeezed. */
export function Pill({ tone = "plain", children }: { tone?: Tone; children: ReactNode }) {
  return (
    <span
      className={`inline-flex h-[22px] flex-none items-center rounded-full px-2.5 text-[12px] leading-none font-medium whitespace-nowrap ${PILL[tone]}`}
    >
      {children}
    </span>
  );
}

/* A business or a person, in their own stable tint. */
export function Mark({ seed, name, size = 28 }: { seed: string; name: string; size?: number }) {
  const style: CSSProperties = {
    ...tintOf(seed),
    width: size,
    height: size,
    fontSize: size >= 36 ? 14 : 11,
  };
  return (
    <span
      aria-hidden
      style={style}
      className="inline-flex flex-none items-center justify-center rounded-full leading-none font-semibold tracking-[0.02em]"
    >
      {initials(name)}
    </span>
  );
}

/* A ratio drawn at its true length, both ends labelled by the caller. */
export function Meter({ share, tone = "plain" }: { share: number; tone?: Tone }) {
  const pct = Math.max(0, Math.min(1, share)) * 100;
  const fill =
    tone === "bad" ? "bg-ad-negative" : tone === "warn" ? "bg-ad-warning" : "bg-ad-accent";
  return (
    <span
      className="bg-ad-raised block h-1.5 w-full overflow-hidden rounded-full"
      role="img"
      aria-label={`${Math.round(pct)}% used`}
    >
      {/* A zero has no stub: nothing used is drawn as nothing. */}
      {pct > 0 ? (
        <span className={`block h-full rounded-full ${fill}`} style={{ width: `${pct}%` }} />
      ) : null}
    </span>
  );
}

/* ---------- states ---------- */

/*
  An empty block keeps its frame and says one sentence, spanning the block.
  On an internal screen empty is usually the healthy answer, and it should
  read that way rather than as a failure to load.
*/
export function Empty({
  title,
  words,
  action,
}: {
  title: string;
  words?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="border-ad-control rounded-[6px] border border-dashed px-5 py-6">
      <p className="text-[13px] leading-[20px] font-medium">{title}</p>
      {words ? (
        <p className="text-ad-muted mt-1 max-w-[70ch] text-[13px] leading-[20px]">{words}</p>
      ) : null}
      {action ? <div className="mt-3 flex flex-wrap gap-x-5 gap-y-2">{action}</div> : null}
    </div>
  );
}

/*
  A read that failed, said inside the block that needed it. Never a banner
  across the screen: the rest of the panel may be fine, and during an
  incident the rest of the panel is exactly what somebody needs.
*/
export function Problem({ words }: { words: string }) {
  if (!words) return null;
  return (
    <p
      role="status"
      className="bg-ad-negative-tint text-ad-text flex items-start gap-2.5 rounded-[6px] px-4 py-3 text-[13px] leading-[20px]"
    >
      <span aria-hidden className="bg-ad-negative mt-[7px] h-1.5 w-1.5 flex-none rounded-full" />
      <span>{words}</span>
    </p>
  );
}

/* ---------- a table that becomes a list on a phone ---------- */

export type Col = {
  key: string;
  label: string;
  num?: boolean;
  /* Left out of the phone's second line. */
  minor?: boolean;
  /* A share of the table's width, for the identity column. */
  width?: string;
};

export type Line = {
  id: string;
  cells: Record<string, ReactNode>;
  /* The row's state, set apart on the phone. */
  tone?: Tone;
};

export function Table({
  cols,
  lines,
  title,
  lead,
  caption,
  stickyHead = false,
}: {
  cols: Col[];
  lines: Line[];
  /* The identity column: line 1 on the phone. */
  title: string;
  /* The key figure: the right of line 1 on the phone. */
  lead?: string;
  caption: string;
  /*
    Keep the header row in view under the top bar while a long page scrolls.
    The panel around it must clip rather than hide its overflow, or the header
    sticks to the panel instead of the window.
  */
  stickyHead?: boolean;
}) {
  const rest = cols.filter((c) => c.key !== title && c.key !== lead && !c.minor);
  return (
    <>
      <div className="hidden md:block">
        <table className="w-full border-collapse text-[13px] leading-[20px]">
          <caption className="sr-only">{caption}</caption>
          <thead>
            <tr>
              {cols.map((c) => (
                <th
                  key={c.key}
                  scope="col"
                  style={c.width ? { width: c.width } : undefined}
                  className={`text-ad-faint h-9 px-5 text-[12px] font-normal whitespace-nowrap ${
                    c.num ? "text-right" : "text-left"
                  } ${
                    stickyHead
                      ? "bg-ad-surface sticky z-10 shadow-[0_1px_0_var(--ad-border)] md:top-14 lg:top-16"
                      : ""
                  }`}
                >
                  {c.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {lines.map((row) => (
              <tr
                key={row.id}
                className="border-ad-rule hover:bg-ad-raised/60 border-t transition-colors duration-150"
              >
                {cols.map((c) => (
                  <td
                    key={c.key}
                    className={`h-[52px] px-5 py-2 align-middle ${
                      c.num ? "ad-num text-right whitespace-nowrap" : "text-left"
                    } ${c.key === title ? "text-ad-text" : "text-ad-muted"}`}
                  >
                    {row.cells[c.key]}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/*
        Phone. The identity and the key figure on line 1, every other field
        the screen names in grey on line 2. Fields move; none is dropped
        except those marked minor.
      */}
      <ul className="md:hidden">
        {lines.map((row) => (
          <li key={row.id} className="border-ad-rule border-t px-4 py-3 first:border-t-0">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0 flex-1">{row.cells[title]}</div>
              {lead ? (
                <div
                  className={`text-ad-text shrink-0 text-right ${
                    cols.find((c) => c.key === lead)?.num ? "ad-num" : ""
                  }`}
                >
                  {row.cells[lead]}
                </div>
              ) : null}
            </div>
            {rest.length ? (
              <dl className="text-ad-faint mt-2 flex flex-wrap gap-x-4 gap-y-1.5 text-[12px] leading-[18px]">
                {rest.map((c) => (
                  <div key={c.key} className="flex items-center gap-1.5">
                    <dt>{c.label}</dt>
                    <dd className={`text-ad-muted ${c.num ? "ad-num" : ""}`}>{row.cells[c.key]}</dd>
                  </div>
                ))}
              </dl>
            ) : null}
          </li>
        ))}
      </ul>
    </>
  );
}

/* ---------- paging ---------- */

/*
  The pages a pager names: always the first and the last, the current one and
  its neighbours, and a gap wherever pages are skipped. "1 ... 4 5 6 ... 52".
*/
function pageList(page: number, pages: number): (number | "gap")[] {
  const keep = new Set([1, pages, page - 1, page, page + 1].filter((n) => n >= 1 && n <= pages));
  const out: (number | "gap")[] = [];
  let last = 0;
  for (const n of [...keep].sort((a, b) => a - b)) {
    if (n - last === 2) out.push(n - 1);
    else if (n - last > 2) out.push("gap");
    out.push(n);
    last = n;
  }
  return out;
}

/*
  A full list's paging: the range in words on the left, the pages on the
  right. Plain links, so every page has its own address and works without a
  script. The current page carries the console's one selection mark, the 1px
  accent line as wide as its number; Previous and Next are the controls, and
  at either end they stay in place, dimmed, so the row does not shift.
*/
export function Pager({
  page,
  per,
  total,
  noun,
  href,
}: {
  page: number;
  per: number;
  total: number;
  /* What is being counted, plural: "runs". */
  noun: string;
  href: (page: number) => string;
}) {
  const pages = Math.max(1, Math.ceil(total / per));
  const from = total ? (page - 1) * per + 1 : 0;
  const to = Math.min(total, page * per);
  const step =
    "inline-flex h-8 items-center gap-1.5 rounded-full px-3 text-[13px] font-medium transition-colors";
  return (
    <nav
      aria-label={`Pages of ${noun}`}
      className="flex flex-wrap items-center justify-between gap-x-6 gap-y-3"
    >
      <p className="text-ad-muted text-[13px] leading-[20px]">
        <span className="ad-num text-ad-text">
          {count(from)}-{count(to)}
        </span>{" "}
        of <span className="ad-num text-ad-text">{count(total)}</span> {noun}
      </p>
      {pages > 1 ? (
        <ul className="flex flex-wrap items-center gap-1">
          <li>
            {page > 1 ? (
              <Link
                href={href(page - 1)}
                rel="prev"
                className={`${step} text-ad-text border-ad-control hover:border-ad-faint border`}
              >
                <CaretLeftIcon size={13} aria-hidden />
                Previous
              </Link>
            ) : (
              <span
                aria-disabled="true"
                className={`${step} border-ad-border text-ad-faint border opacity-60`}
              >
                <CaretLeftIcon size={13} aria-hidden />
                Previous
              </span>
            )}
          </li>
          {/*
            On a phone the numbers would wrap the row onto two lines, so it
            says where you are in words between the two controls instead.
          */}
          <li className="text-ad-muted px-2 text-[13px] sm:hidden">
            Page <span className="ad-num text-ad-text">{count(page)}</span> of{" "}
            <span className="ad-num">{count(pages)}</span>
          </li>
          {pageList(page, pages).map((n, at) =>
            n === "gap" ? (
              <li
                key={`gap-${at}`}
                aria-hidden
                className="text-ad-faint px-1.5 text-[13px] max-sm:hidden"
              >
                &hellip;
              </li>
            ) : (
              <li key={n} className="max-sm:hidden">
                <Link
                  href={href(n)}
                  aria-label={`Page ${n}`}
                  aria-current={n === page ? "page" : undefined}
                  className={`ad-num relative inline-flex h-8 min-w-8 items-center justify-center px-2 text-[13px] transition-colors ${
                    n === page ? "text-ad-text font-medium" : "text-ad-faint hover:text-ad-text"
                  }`}
                >
                  {count(n)}
                  {n === page ? (
                    <span
                      aria-hidden
                      className="bg-ad-accent absolute right-2 bottom-1 left-2 h-px"
                    />
                  ) : null}
                </Link>
              </li>
            ),
          )}
          <li>
            {page < pages ? (
              <Link
                href={href(page + 1)}
                rel="next"
                className={`${step} text-ad-text border-ad-control hover:border-ad-faint border`}
              >
                Next
                <CaretRightIcon size={13} aria-hidden />
              </Link>
            ) : (
              <span
                aria-disabled="true"
                className={`${step} border-ad-border text-ad-faint border opacity-60`}
              >
                Next
                <CaretRightIcon size={13} aria-hidden />
              </span>
            )}
          </li>
        </ul>
      ) : null}
    </nav>
  );
}

/* ---------- buttons ---------- */

/*
  One filled primary per screen, near-white on the dark ground; a secondary
  outlined; a destructive one outlined in the negative colour, never filled,
  because the most consequential button in the product should not also be the
  loudest thing on the screen by accident.
*/
export const BUTTON = {
  primary:
    "bg-ad-text text-ad-ground hover:bg-white inline-flex h-[34px] items-center gap-2 rounded-full px-4 text-[13px] font-semibold transition-[background-color,transform] duration-150 active:scale-[0.98] disabled:opacity-50",
  quiet:
    "border-ad-control text-ad-text hover:border-ad-faint inline-flex h-[34px] items-center gap-2 rounded-full border px-4 text-[13px] font-medium transition-[border-color,transform] duration-150 active:scale-[0.98] disabled:opacity-50",
  danger:
    "border-ad-negative/60 text-ad-negative hover:border-ad-negative hover:bg-ad-negative-tint inline-flex h-[34px] items-center gap-2 rounded-full border px-4 text-[13px] font-semibold transition-[background-color,border-color,transform] duration-150 active:scale-[0.98] disabled:opacity-50",
};

/* The field style, for the few forms the console has. */
export const FIELD =
  "border-ad-control bg-ad-ground text-ad-text placeholder:text-ad-faint focus:border-ad-accent h-[38px] w-full rounded-[6px] border px-3 text-[13px] outline-none transition-colors";
