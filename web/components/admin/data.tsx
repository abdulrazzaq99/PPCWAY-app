import type { ReactNode } from "react";

/*
  The internal panel's own data surface.

  It stopped using the merchant app's blocks, and that is the whole point of
  this file. Those blocks encode a merchant's rhythm: roomy cards, a reassuring
  sentence above every number, one idea per screenful. That is right for
  somebody looking at their own business once a week and wrong for somebody
  scanning four hundred of them at two in the morning. Seven screens built from
  PageHead + TabsRow + DataTable all looked like the same screen, because they
  were.

  Same tokens, same palette, same radii. Different density.

  Three things this fixes that the merchant blocks could not:

  **It works on a phone.** `DataTable` is `min-w-[820px]` inside
  `overflow-x-auto`, so every admin screen was a horizontal scrollbar on a
  handset. Here the table is the desktop presentation and a stacked list is the
  mobile one; neither is a squeezed version of the other.

  **Numbers line up.** `.pw-num` has carried `font-variant-numeric:
  tabular-nums` since the app was built and nothing in the panel used it. In a
  column of figures that is the difference between reading and counting.

  **Hairlines, not boxes.** At this density a card around every group is noise.
  A 1px line does the same work and leaves the figures room.
*/

/* ---------- the line that matters ---------- */

export function Attention({ items }: { items: string[] }) {
  /*
    What is wrong, first, before any figure. Somebody opening an internal
    screen is looking for the thing that is broken; four tiles above it is four
    tiles in their way.
  */
  if (!items.length) return null;
  return (
    <ul className="border-pw-bad/30 bg-pw-bad-bg space-y-2 rounded-[12px] border px-4 py-3 sm:px-5 sm:py-4">
      {items.map((one) => (
        <li key={one} className="text-pw-bad-ink text-[14px] leading-[20px]">
          {one}
        </li>
      ))}
    </ul>
  );
}

export function AllWell({ words }: { words: string }) {
  return (
    <p className="text-pw-ink-600 border-pw-border mb-6 border-l-2 pl-4 text-[14px] leading-[20px]">
      {words}
    </p>
  );
}

/* ---------- figures ---------- */

export type Stat = {
  label: string;
  value: string;
  /* A short qualifier: the window, or which way it moved. */
  note?: string;
  /* Colour on the note says good or bad for this figure, never up or down. */
  noteTone?: "plain" | "good" | "bad";
  tone?: "plain" | "warn" | "bad";
  unknown?: boolean;
  /*
    The one figure that answers the screen's question. It is set larger than
    its siblings, because a strip of five equal numbers leaves the screen
    without a lead and the reader has to pick one themselves.
  */
  lead?: boolean;
};

export function Stats({ stats }: { stats: Stat[] }) {
  const odd = stats.length % 2 === 1;
  /*
    A strip rather than a row of cards. Hairlines between on desktop, stacked
    pairs on a phone. Two columns on a handset rather than one: these are short
    values and a single column wastes the screen that is already smallest.
  */
  return (
    <dl className="border-pw-border divide-pw-border grid grid-cols-2 gap-px overflow-hidden rounded-[12px] border bg-[var(--pw-border)] sm:grid-cols-3 lg:grid-cols-5">
      {stats.map((one, at) => (
        <div
          key={one.label}
          className={[
            "bg-pw-card px-4 py-3 sm:px-5 sm:py-4",
            /*
              An odd number of figures in a two-column grid leaves a hole at
              the end, which reads as a missing tile rather than a choice. The
              last one spans the row instead. Only at the two-column
              breakpoint: three and five columns divide these counts fine.
            */
            odd && at === stats.length - 1 ? "col-span-2 sm:col-span-1" : "",
          ].join(" ")}
        >
          <dt className="text-pw-ink-500 text-[13px] leading-[18px]">{one.label}</dt>
          <dd
            className={[
              "pw-num mt-1 font-normal",
              one.lead
                ? "text-[28px] leading-[34px] font-medium sm:text-[32px] sm:leading-[38px]"
                : "text-[20px] leading-[26px] sm:text-[22px] sm:leading-[28px]",
              one.unknown
                ? "text-pw-ink-300"
                : one.tone === "bad"
                  ? "text-pw-bad"
                  : one.tone === "warn"
                    ? "text-pw-warn"
                    : "text-pw-ink",
            ].join(" ")}
          >
            {one.unknown ? "Unknown" : one.value}
          </dd>
          {one.note ? (
            <p
              className={`mt-0.5 text-[12px] leading-[16px] ${
                one.noteTone === "bad"
                  ? "text-pw-bad"
                  : one.noteTone === "good"
                    ? "text-pw-good"
                    : "text-pw-ink-500"
              }`}
            >
              {one.note}
            </p>
          ) : null}
        </div>
      ))}
    </dl>
  );
}

/* ---------- rows ---------- */

export type Col = {
  key: string;
  label: string;
  /* Right-aligned and tabular. Use for anything countable. */
  num?: boolean;
  /* Dropped from the phone layout. Not every column earns its place there. */
  minor?: boolean;
  width?: number;
};

export type Row = { id: string } & Record<string, ReactNode>;

export function Rows({
  cols,
  rows,
  empty,
  /* What identifies a row when it collapses to a card. */
  titleKey,
}: {
  cols: Col[];
  rows: Row[];
  empty: ReactNode;
  titleKey: string;
}) {
  if (!rows.length) return <>{empty}</>;
  const rest = cols.filter((c) => c.key !== titleKey);
  const onPhone = rest.filter((c) => !c.minor);

  return (
    <>
      {/*
        Desktop. A real table, because a table of comparable values is what
        this is and anything else would be a worse table.
      */}
      <div className="border-pw-border hidden overflow-hidden rounded-[12px] border md:block">
        <table className="w-full border-collapse text-[14px]">
          <thead>
            <tr className="border-pw-border bg-pw-muted border-b">
              {cols.map((c) => (
                <th
                  key={c.key}
                  scope="col"
                  style={c.width ? { width: c.width } : undefined}
                  className={`text-pw-ink-500 px-4 py-2.5 text-[12px] leading-[16px] font-medium ${
                    c.num ? "text-right" : "text-left"
                  }`}
                >
                  {c.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-pw-divider divide-y">
            {rows.map((row) => (
              <tr key={row.id} className="hover:bg-pw-row-hover">
                {cols.map((c) => (
                  <td
                    key={c.key}
                    className={`text-pw-ink-700 px-4 py-2.5 align-top ${
                      c.num ? "pw-num text-right" : "text-left"
                    }`}
                  >
                    {row[c.key]}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/*
        Phone. Not the same table squeezed: a list where each row's identifier
        is the heading and the rest are labelled pairs. Minor columns are left
        out entirely rather than shrunk to nothing.
      */}
      <ul className="border-pw-border divide-pw-divider divide-y overflow-hidden rounded-[12px] border md:hidden">
        {rows.map((row) => (
          <li key={row.id} className="px-4 py-3">
            <p className="text-pw-ink text-[15px] leading-[21px] font-semibold">{row[titleKey]}</p>
            <dl className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1.5">
              {onPhone.map((c) => (
                <div key={c.key} className="flex items-baseline justify-between gap-2">
                  <dt className="text-pw-ink-500 text-[12px] leading-[16px]">{c.label}</dt>
                  <dd
                    className={`text-pw-ink-700 text-[13px] leading-[18px] ${
                      c.num ? "pw-num" : ""
                    }`}
                  >
                    {row[c.key]}
                  </dd>
                </div>
              ))}
            </dl>
          </li>
        ))}
      </ul>
    </>
  );
}

/* ---------- empty states ---------- */

export function Nothing({ title, words }: { title: string; words: string }) {
  /*
    An empty internal screen is usually the healthy answer, and it should read
    that way rather than looking like a failure to load.
  */
  return (
    <div className="border-pw-border rounded-[12px] border border-dashed px-5 py-8 text-center">
      <p className="text-pw-ink text-[15px] leading-[21px] font-medium">{title}</p>
      <p className="text-pw-ink-500 mx-auto mt-1 max-w-[46ch] text-[14px] leading-[20px]">
        {words}
      </p>
    </div>
  );
}

/* ---------- the page frame ---------- */

export function Page({
  title,
  lead,
  side,
  children,
}: {
  title: string;
  lead?: string;
  side?: ReactNode;
  children: ReactNode;
}) {
  /*
    The sheet's own scroll, so the sidebar stays put and the work does not
    float in a page three hundred pixels taller than it. The title is 24px:
    the study's median for a screen that has a heading at all, and nine of its
    twenty-three have nothing over 16.
  */
  return (
    <main className="h-full overflow-y-auto px-4 py-5 sm:px-6 sm:py-6">
      <header className="mb-5 flex flex-wrap items-end justify-between gap-3">
        <div className="min-w-0">
          <h1 className="text-pw-ink text-[19px] leading-[25px] font-semibold sm:text-[22px] sm:leading-[28px]">
            {title}
          </h1>
          {lead ? (
            <p className="text-pw-ink-600 mt-1 max-w-[70ch] text-[14px] leading-[20px]">{lead}</p>
          ) : null}
        </div>
        {side ? <div className="shrink-0">{side}</div> : null}
      </header>
      {children}
    </main>
  );
}

/* A word with a state behind it. Colour is never the only signal. */
export function State({
  tone = "plain",
  children,
}: {
  tone?: "plain" | "good" | "warn" | "bad" | "faint";
  children: ReactNode;
}) {
  const look = {
    plain: "text-pw-ink-700",
    good: "text-pw-good",
    warn: "text-pw-warn",
    bad: "text-pw-bad",
    faint: "text-pw-ink-500",
  }[tone];
  return <span className={`text-[13px] leading-[18px] ${look}`}>{children}</span>;
}
