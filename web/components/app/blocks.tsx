import Link from "next/link";
import type { ReactNode } from "react";
import { Button, LinkButton } from "@/components/ui/button";
import { cn } from "@/lib/cn";

/*
  The dashboard building blocks, measured from the "V2 Dashboard · Desktop 1440" frames.
  A page is: a headline block (34/41 headline, 17/21 subline), a row of four tiles,
  then two columns: 728px of panels on the left and a 368px aside on the right.
  On a phone the tiles become one hero tile and a pair, and the columns stack.
*/

/* ---------- Headline block ---------- */
export function PageHead({
  title,
  lead,
  action,
  className,
}: {
  title: string;
  lead?: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-wrap items-end justify-between gap-4", className)}>
      <div className="max-w-[1112px] min-w-0">
        <h1 className="text-ink text-[28px] leading-[34px] font-semibold text-balance lg:text-[34px] lg:leading-[41px]">
          {title}
        </h1>
        {lead ? (
          <p className="text-muted mt-[6px] text-[15px] leading-[19px] lg:mt-[10px] lg:text-[17px] lg:leading-[21px]">
            {lead}
          </p>
        ) : null}
      </div>
      {action ? <div className="flex shrink-0 items-center gap-3">{action}</div> : null}
    </div>
  );
}

/* ---------- Tiles ---------- */
type TileTone = "brand" | "panel" | "red" | "amber";

const tileTones: Record<TileTone, { box: string; label: string; value: string; chip: string }> = {
  brand: {
    box: "bg-brand",
    label: "text-brand-label",
    value: "text-white",
    chip: "bg-brand-dark text-white",
  },
  panel: {
    box: "bg-panel border border-line",
    label: "text-muted",
    value: "text-ink",
    chip: "bg-brand-tint text-brand",
  },
  red: {
    box: "bg-red-strong",
    label: "text-red-label",
    value: "text-white",
    chip: "bg-red text-white",
  },
  amber: {
    box: "bg-amber",
    label: "text-amber-pale",
    value: "text-white",
    chip: "bg-amber-dark text-white",
  },
};

export type ChipTone = "brand" | "grey" | "red" | "amber" | "pale";
const chipTones: Record<ChipTone, string> = {
  brand: "bg-brand-tint text-brand",
  pale: "bg-brand-pale text-brand-dark",
  grey: "bg-line-soft text-muted",
  red: "bg-red-pale text-red",
  amber: "bg-amber-pale text-amber-dark",
};

export function Tiles({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div
      className={cn(
        "mt-[26px] grid grid-cols-2 gap-[14px] lg:grid-cols-4 lg:gap-4 [&>*:first-child]:col-span-2 lg:[&>*:first-child]:col-span-1 [&>*:nth-child(4)]:col-span-2 lg:[&>*:nth-child(4)]:col-span-1",
        className,
      )}
    >
      {children}
    </div>
  );
}

export function Tile({
  label,
  value,
  chip,
  chipTone,
  progress,
  tone = "panel",
  valueTone,
}: {
  label: string;
  value: string;
  chip?: string;
  chipTone?: ChipTone;
  /** 0 to 1, draws the 8px track instead of a chip. */
  progress?: number;
  tone?: TileTone;
  /** Overrides the value colour, for "Too early" in faint or "Missing" in red. */
  valueTone?: "faint" | "red";
}) {
  const t = tileTones[tone];
  const hero = tone !== "panel";
  return (
    <div
      className={cn(
        "flex flex-col rounded-[16px] px-5 py-5 lg:min-h-[134px]",
        hero && "rounded-[20px] lg:rounded-[16px]",
        t.box,
      )}
    >
      <p className={cn("text-[13px] leading-4 font-medium", t.label)}>{label}</p>
      <p
        className={cn(
          "mt-2 text-[26px] leading-[31px] font-semibold lg:text-[32px] lg:leading-[39px]",
          hero && "text-[36px] leading-[44px]",
          t.value,
          valueTone === "faint" && "text-faint",
          valueTone === "red" && "text-red-strong",
        )}
      >
        {value}
      </p>
      {progress !== undefined ? (
        <div className="bg-track [margin-top:14px] mt-auto h-2 w-full overflow-hidden rounded-full pt-0">
          <div
            className="bg-brand h-full rounded-full"
            style={{ width: `${Math.round(progress * 100)}%` }}
          />
        </div>
      ) : chip ? (
        <span
          className={cn(
            "mt-2 inline-flex h-[23px] w-fit max-w-full items-center rounded-full px-[10px] text-[12px] leading-[15px] font-semibold whitespace-nowrap",
            !hero && "hidden sm:inline-flex",
            chipTone ? chipTones[chipTone] : t.chip,
          )}
        >
          <span className="truncate">{chip}</span>
        </span>
      ) : null}
    </div>
  );
}

/* ---------- Columns ---------- */
export function Columns({
  children,
  aside,
  className,
}: {
  children: ReactNode;
  aside?: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("mt-[26px] grid gap-4 lg:grid-cols-[minmax(0,728px)_368px]", className)}>
      <div className="flex min-w-0 flex-col gap-4">{children}</div>
      {aside ? <div className="flex min-w-0 flex-col gap-4">{aside}</div> : null}
    </div>
  );
}

/* ---------- Panel ---------- */
type PanelTone = "panel" | "amber" | "red" | "plain";
const panelTones: Record<PanelTone, string> = {
  panel: "bg-panel border border-line",
  plain: "bg-panel",
  amber: "bg-amber-tint border border-amber-line",
  red: "bg-panel border border-red-line",
};

export function Panel({
  title,
  action,
  children,
  tone = "panel",
  className,
  as: Tag = "section",
}: {
  title?: ReactNode;
  /** A text link at the right of the header, or any node. */
  action?: { label: string; href?: string; tone?: "brand" | "muted" } | ReactNode;
  children?: ReactNode;
  tone?: PanelTone;
  className?: string;
  as?: "section" | "div" | "article";
}) {
  return (
    <Tag
      className={cn("rounded-[16px] px-5 py-5 lg:px-6 lg:py-[22px]", panelTones[tone], className)}
    >
      {title ? (
        <header className="flex items-start justify-between gap-4">
          <h2 className="text-ink text-[16px] leading-[19px] font-semibold">{title}</h2>
          {isAction(action) ? <HeaderLink {...action} /> : action}
        </header>
      ) : null}
      {children}
    </Tag>
  );
}

type ActionSpec = { label: string; href?: string; tone?: "brand" | "muted" };
function isAction(a: unknown): a is ActionSpec {
  return Boolean(a) && typeof a === "object" && "label" in (a as object);
}
export function HeaderLink({ label, href, tone = "brand" }: ActionSpec) {
  const cls = cn(
    "shrink-0 text-[14px] leading-[17px] font-semibold",
    tone === "brand" ? "text-brand hover:text-brand-dark" : "text-faint",
  );
  return href ? (
    <Link href={href} className={cls}>
      {label}
    </Link>
  ) : (
    <button type="button" className={cls}>
      {label}
    </button>
  );
}

/** The 19/23 sentence under a panel title. */
export function Summary({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <p
      className={cn(
        "text-ink mt-[18px] text-[17px] leading-[21px] font-medium lg:text-[19px] lg:leading-[23px]",
        className,
      )}
    >
      {children}
    </p>
  );
}

/** The 13/16 faint line at the foot of a panel. */
export function Footnote({ children, className }: { children: ReactNode; className?: string }) {
  return <p className={cn("text-faint mt-4 text-[13px] leading-4", className)}>{children}</p>;
}

/** A 14/17 muted paragraph inside a panel. */
export function PanelText({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <p className={cn("text-muted mt-[10px] text-[14px] leading-[17px]", className)}>{children}</p>
  );
}

/* ---------- Rows ---------- */
export function Rows({ children, className }: { children: ReactNode; className?: string }) {
  return <ul className={cn("divide-line-soft mt-[10px] divide-y", className)}>{children}</ul>;
}

export type RowIcon = "bars" | "plus" | "line" | "bar" | "none" | "check" | "cross";
export type IconTone = "brand" | "amber" | "grey" | "red";
const iconTones: Record<IconTone, { box: string; mark: string }> = {
  brand: { box: "bg-brand-pale", mark: "bg-brand" },
  amber: { box: "bg-amber-chip", mark: "bg-amber" },
  grey: { box: "bg-grey-chip", mark: "bg-grey-dot" },
  red: { box: "bg-red-pale", mark: "bg-red-strong" },
};

export function RowGlyph({ icon, tone = "brand" }: { icon: RowIcon; tone?: IconTone }) {
  const t = iconTones[tone];
  return (
    <span aria-hidden className={cn("relative block size-9 shrink-0 rounded-[11px]", t.box)}>
      {icon === "bars" ? (
        <>
          <span className={cn(t.mark, "absolute top-[11px] left-3 h-[14px] w-1 rounded-[2px]")} />
          <span className={cn(t.mark, "absolute top-[11px] left-5 h-[14px] w-1 rounded-[2px]")} />
        </>
      ) : icon === "plus" ? (
        <>
          <span className={cn(t.mark, "absolute top-4 left-[11px] h-1 w-[14px] rounded-[2px]")} />
          <span className={cn(t.mark, "absolute top-[11px] left-4 h-[14px] w-1 rounded-[2px]")} />
        </>
      ) : icon === "line" ? (
        <span className={cn(t.mark, "absolute top-4 left-[11px] h-1 w-[14px] rounded-[2px]")} />
      ) : icon === "bar" ? (
        <span className={cn(t.mark, "absolute top-[11px] left-4 h-[14px] w-1 rounded-[2px]")} />
      ) : icon === "check" ? (
        <span
          className={cn(
            "absolute top-[9px] left-[13px] h-[14px] w-[8px] rotate-45 border-r-[3px] border-b-[3px]",
            tone === "brand"
              ? "border-brand"
              : tone === "amber"
                ? "border-amber"
                : tone === "red"
                  ? "border-red-strong"
                  : "border-grey-dot",
          )}
        />
      ) : icon === "cross" ? (
        <>
          <span
            className={cn(
              t.mark,
              "absolute top-4 left-[11px] h-1 w-[14px] rotate-45 rounded-[2px]",
            )}
          />
          <span
            className={cn(
              t.mark,
              "absolute top-4 left-[11px] h-1 w-[14px] -rotate-45 rounded-[2px]",
            )}
          />
        </>
      ) : null}
    </span>
  );
}

/** The 66px activity row: a glyph, a sentence, a meta line, and a text action. */
export function ActivityRow({
  icon = "line",
  iconTone = "grey",
  title,
  meta,
  metaTone = "faint",
  action,
  actionTone = "brand",
  href,
  selected,
  muted,
}: {
  icon?: RowIcon;
  iconTone?: IconTone;
  title: ReactNode;
  meta?: ReactNode;
  metaTone?: "faint" | "amber" | "red" | "brand";
  action?: string;
  actionTone?: "brand" | "amber" | "red" | "faint";
  href?: string;
  /** The row in use: pale fill and a solid brand glyph. */
  selected?: boolean;
  /** Greyed title, for an option that is not open yet. */
  muted?: boolean;
}) {
  const metaCls = {
    faint: "text-faint",
    amber: "text-amber font-semibold",
    red: "text-red-strong font-semibold",
    brand: "text-brand font-semibold",
  }[metaTone];
  const actionCls = {
    brand: "text-brand",
    amber: "text-amber-dark",
    red: "text-red-strong",
    faint: "text-faint",
  }[actionTone];
  return (
    <li
      className={cn(
        "flex items-start gap-[14px] py-[14px] first:pt-[10px]",
        selected && "bg-brand-pale -mx-3 rounded-[10px] px-3",
      )}
    >
      {selected ? (
        <span aria-hidden className="bg-brand relative block size-9 shrink-0 rounded-[11px]">
          <span className="absolute top-4 left-[11px] h-1 w-[14px] rounded-[2px] bg-white" />
          <span className="absolute top-[11px] left-4 h-[14px] w-1 rounded-[2px] bg-white" />
        </span>
      ) : (
        <RowGlyph icon={icon} tone={iconTone} />
      )}
      <div className="min-w-0 flex-1">
        <p
          className={cn(
            "text-[15px] leading-[18px] font-medium",
            muted ? "text-faint" : "text-ink",
          )}
        >
          {title}
        </p>
        {meta ? <p className={cn("mt-1 text-[13px] leading-4", metaCls)}>{meta}</p> : null}
      </div>
      {action ? (
        href ? (
          <Link
            href={href}
            className={cn("shrink-0 pt-[3px] text-[14px] leading-[17px] font-semibold", actionCls)}
          >
            {action}
          </Link>
        ) : (
          <button
            type="button"
            className={cn("shrink-0 pt-[3px] text-[14px] leading-[17px] font-semibold", actionCls)}
          >
            {action}
          </button>
        )
      ) : null}
    </li>
  );
}

/** The 61px list row: a title, a meta line, and a status pill or a value on the right. */
export function ListRow({
  title,
  meta,
  chip,
  chipTone = "grey",
  dot,
  right,
  href,
  titleWeight = "medium",
}: {
  title: ReactNode;
  meta?: ReactNode;
  chip?: string;
  chipTone?: ChipTone;
  /** Draw the 7px dot before the chip label, as on the campaign status pills. */
  dot?: boolean;
  right?: ReactNode;
  href?: string;
  titleWeight?: "medium" | "semibold";
}) {
  const inner = (
    <>
      <div className="min-w-0 flex-1">
        <p
          className={cn(
            "text-ink text-[15px] leading-[18px]",
            titleWeight === "medium" ? "font-medium" : "font-semibold",
          )}
        >
          {title}
        </p>
        {meta ? <p className="text-faint mt-[3px] text-[13px] leading-4">{meta}</p> : null}
      </div>
      {chip ? (
        <StatusPill tone={chipTone} dot={dot}>
          {chip}
        </StatusPill>
      ) : (
        right
      )}
      {href ? (
        <span aria-hidden className="text-faint text-[20px] leading-6 font-semibold">
          ›
        </span>
      ) : null}
    </>
  );
  return (
    <li>
      {href ? (
        <Link
          href={href}
          className="hover:bg-line-soft -mx-2 flex items-center gap-3 rounded-[10px] px-2 py-3 transition-colors duration-[var(--dur-hover)]"
        >
          {inner}
        </Link>
      ) : (
        <div className="flex items-center gap-3 py-3">{inner}</div>
      )}
    </li>
  );
}

export function StatusPill({
  tone = "grey",
  dot,
  children,
  className,
}: {
  tone?: ChipTone;
  dot?: boolean;
  children: ReactNode;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center gap-[6px] rounded-full px-[10px] text-[12px] leading-[15px] font-semibold whitespace-nowrap",
        dot ? "h-[25px]" : "h-[23px]",
        chipTones[tone],
        className,
      )}
    >
      {dot ? (
        <span
          aria-hidden
          className={cn("size-[7px] rounded-full", tone === "grey" ? "bg-grey-dot" : "bg-current")}
        />
      ) : null}
      {children}
    </span>
  );
}

/* ---------- The grey inner card (an ad preview, or any four-line example) ---------- */
export function AdMock({
  kicker,
  source,
  headline,
  headlineTone = "ink",
  body,
  children,
  className,
}: {
  kicker: string;
  source?: ReactNode;
  headline: ReactNode;
  headlineTone?: "ink" | "link" | "red";
  body?: ReactNode;
  children?: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("bg-ad-bg mt-4 rounded-[12px] px-5 py-[18px]", className)}>
      <p className="text-muted text-[12px] leading-[15px] font-semibold">{kicker}</p>
      {source ? <p className="text-muted mt-[6px] text-[13px] leading-4">{source}</p> : null}
      <p
        className={cn(
          "mt-[6px] text-[17px] leading-[21px] font-medium lg:text-[19px] lg:leading-[23px]",
          headlineTone === "link"
            ? "text-ad-link"
            : headlineTone === "red"
              ? "text-red-strong"
              : "text-ink",
        )}
      >
        {headline}
      </p>
      {body ? <p className="text-muted mt-[6px] text-[14px] leading-[17px]">{body}</p> : null}
      {children}
    </div>
  );
}

/* ---------- The aside card that asks for something ---------- */
type NoticeTone = "amber" | "red" | "panel" | "brand";
const noticeTones: Record<
  NoticeTone,
  { box: string; tag: ChipTone | "amber-tag" | "red-tag"; secondary: string }
> = {
  amber: {
    box: "bg-amber-tint border-amber-line",
    tag: "amber",
    secondary: "border-[#e6cea4] text-amber-dark hover:bg-amber-pale",
  },
  red: {
    box: "bg-red-pale border-[#f2d4d3]",
    tag: "red",
    secondary: "border-[#e6bfbe] text-red hover:bg-red-chip",
  },
  panel: {
    box: "bg-panel border-line",
    tag: "grey",
    secondary: "border-line-input text-muted hover:bg-line-soft",
  },
  brand: {
    box: "bg-panel border-line",
    tag: "pale",
    secondary: "border-line-input text-muted hover:bg-line-soft",
  },
};

export function NoticeCard({
  tone = "amber",
  tag,
  tagTone,
  title,
  body,
  primary,
  primaryTone,
  secondary,
  link,
  children,
  className,
  compact,
}: {
  tone?: NoticeTone;
  tag?: string;
  tagTone?: ChipTone;
  title: ReactNode;
  body?: ReactNode;
  primary?: { label: string; href?: string; working?: string };
  primaryTone?: "brand" | "red" | "ink" | "secondary";
  secondary?: { label: string; href?: string };
  /** A text link instead of buttons. */
  link?: { label: string; href?: string };
  children?: ReactNode;
  className?: string;
  /** The 16/19 title used by the "One thing left" style panel. */
  compact?: boolean;
}) {
  const t = noticeTones[tone];
  const tagCls =
    tone === "red" ? "bg-red-chip text-red" : chipTones[(tagTone ?? t.tag) as ChipTone];
  const primaryCls =
    primaryTone === "red"
      ? "bg-red-strong hover:bg-red text-white"
      : primaryTone === "ink"
        ? "bg-rail hover:bg-rail-soft text-white"
        : primaryTone === "secondary"
          ? "bg-panel border border-line text-ink hover:bg-line-soft"
          : undefined;
  return (
    <section
      className={cn("rounded-[16px] border px-5 py-5 lg:px-6 lg:py-[22px]", t.box, className)}
    >
      {tag ? (
        <span
          className={cn(
            "inline-flex h-[26px] items-center rounded-full px-3 text-[13px] leading-4 font-semibold",
            tagCls,
          )}
        >
          {tag}
        </span>
      ) : null}
      <h2
        className={cn(
          "text-ink font-semibold",
          tag && "mt-3",
          compact
            ? "text-[16px] leading-[19px]"
            : "text-[18px] leading-[22px] lg:text-[19px] lg:leading-[23px]",
        )}
      >
        {title}
      </h2>
      {body ? (
        <p
          className={cn(
            "text-muted mt-[10px]",
            compact ? "text-[14px] leading-[17px]" : "text-[15px] leading-[18px]",
          )}
        >
          {body}
        </p>
      ) : null}
      {children}
      {primary || secondary ? (
        <div className="mt-[18px] flex flex-wrap items-center gap-[10px]">
          {primary ? (
            primary.href ? (
              <LinkButton
                href={primary.href}
                size="sm"
                className={cn("h-11 px-6 text-[15px]", primaryCls)}
              >
                {primary.label}
              </LinkButton>
            ) : (
              <Button size="sm" className={cn("h-11 px-6 text-[15px]", primaryCls)}>
                {primary.label}
              </Button>
            )
          ) : null}
          {secondary ? (
            secondary.href ? (
              <Link
                href={secondary.href}
                className={cn(
                  "inline-flex h-[46px] items-center rounded-full border bg-transparent px-[21px] text-[15px] leading-[18px] font-semibold transition-colors",
                  t.secondary,
                )}
              >
                {secondary.label}
              </Link>
            ) : (
              <button
                type="button"
                className={cn(
                  "inline-flex h-[46px] items-center rounded-full border bg-transparent px-[21px] text-[15px] leading-[18px] font-semibold transition-colors",
                  t.secondary,
                )}
              >
                {secondary.label}
              </button>
            )
          ) : null}
        </div>
      ) : null}
      {link ? (
        <Link
          href={link.href ?? "#"}
          className="text-brand mt-3 inline-block text-[14px] leading-[17px] font-semibold"
        >
          {link.label}
        </Link>
      ) : null}
    </section>
  );
}

/* ---------- Small pieces ---------- */
/** The white pill used for a term or a keyword inside a proposal. */
export function TermPill({
  children,
  tone = "amber",
}: {
  children: ReactNode;
  tone?: "amber" | "line";
}) {
  return (
    <span
      className={cn(
        "bg-panel text-ink inline-flex h-[31px] items-center rounded-full border px-[13px] text-[14px] leading-[17px] font-medium",
        tone === "amber" ? "border-amber-line" : "border-line",
      )}
    >
      {children}
    </span>
  );
}

/** The before-and-after strip inside a proposal. */
export function BeforeAfter({
  label,
  before,
  after,
}: {
  label: string;
  before: string;
  after: string;
}) {
  return (
    <div className="bg-panel mt-3 flex flex-wrap items-center gap-x-7 gap-y-1 rounded-[12px] px-[18px] py-[14px]">
      <span className="text-faint text-[14px] leading-[17px] font-medium">{label}</span>
      <span className="text-ink text-[15px] leading-[18px] font-medium">{before}</span>
      <span className="text-brand text-[15px] leading-[18px] font-semibold">{after}</span>
    </div>
  );
}

/** A 46px row with a name on the left and a status sentence on the right. */
export function DecidedRow({
  name,
  status,
  tone = "brand",
}: {
  name: string;
  status: string;
  tone?: "brand" | "faint";
}) {
  return (
    <li className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 py-[14px]">
      <span className="text-ink text-[15px] leading-[18px] font-medium">{name}</span>
      <span
        className={cn(
          "text-[14px] leading-[17px] font-medium",
          tone === "brand" ? "text-brand" : "text-faint",
        )}
      >
        {status}
      </span>
    </li>
  );
}

/** The 72px navy selection bar under a table. */
export function SelectionBar({ text, children }: { text: string; children: ReactNode }) {
  return (
    <div className="bg-rail mt-[26px] flex flex-wrap items-center justify-between gap-3 rounded-[16px] px-5 py-[14px]">
      <p className="text-[15px] leading-[18px] font-semibold text-white">{text}</p>
      <div className="flex flex-wrap items-center gap-[10px]">{children}</div>
    </div>
  );
}

/** The row of tab pills above a table, with an optional button at the right. */
export function TabsRow({
  tabs,
  active,
  action,
}: {
  tabs: { label: string; href: string }[];
  active: string;
  action?: ReactNode;
}) {
  return (
    <div className="mt-[26px] flex flex-wrap items-center justify-between gap-3">
      <nav className="flex flex-wrap items-center gap-2" aria-label="Views">
        {tabs.map((t) =>
          t.label === active ? (
            <span
              key={t.label}
              className="bg-rail flex h-[33px] items-center rounded-full px-4 text-[14px] leading-[17px] font-semibold text-white"
            >
              {t.label}
            </span>
          ) : (
            <Link
              key={t.label}
              href={t.href}
              className="text-muted hover:text-ink flex h-[33px] items-center px-2 text-[14px] leading-[17px] font-medium"
            >
              {t.label}
            </Link>
          ),
        )}
      </nav>
      {action}
    </div>
  );
}

/** The two-option control drawn at the top right of the chart. */
export function Segmented({ options, active }: { options: string[]; active: string }) {
  return (
    <div className="bg-line-soft flex h-8 items-center rounded-full p-[3px]">
      {options.map((o) => (
        <button
          key={o}
          type="button"
          className={cn(
            "h-[26px] rounded-full px-3 text-[13px] leading-4 font-medium",
            o === active ? "bg-panel text-ink shadow-[0_0_0_1px_var(--line)]" : "text-muted",
          )}
        >
          {o}
        </button>
      ))}
    </div>
  );
}

/** The weekly bar chart: soft bars, this week in brand, a value pill over the last bar. */
export function BarChart({
  bars,
  highlight,
  pill,
  axisStart,
  axisEnd = "This week",
  footnote,
  tone = "brand",
}: {
  /** Heights as a fraction of the tallest bar. */
  bars: number[];
  /** Index of the highlighted bar; defaults to the last. */
  highlight?: number;
  pill?: string;
  axisStart: string;
  axisEnd?: string;
  footnote?: string;
  tone?: "brand" | "red" | "amber";
}) {
  const hi = highlight ?? bars.length - 1;
  const hiCls = tone === "red" ? "bg-red-strong" : tone === "amber" ? "bg-amber" : "bg-brand";
  return (
    <div className="mt-[18px]">
      <div className="relative h-[178px]">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="bg-line-soft absolute inset-x-0 h-px"
            style={{ top: `${(i / 3) * 100}%` }}
          />
        ))}
        <span className="absolute inset-x-0 bottom-0 h-px bg-[#dbe2e7]" />
        <div className="absolute inset-x-0 bottom-0 flex items-end justify-around gap-2 px-2 lg:px-6">
          {bars.map((b, i) => (
            <div key={i} className="relative flex w-full max-w-[56px] flex-col items-center">
              {i === hi && pill ? (
                <span className="bg-rail absolute -top-[34px] rounded-full px-[10px] py-1 text-[12px] leading-[15px] font-semibold whitespace-nowrap text-white">
                  {pill}
                </span>
              ) : null}
              <span
                className={cn("block w-full rounded-t-[7px]", i === hi ? hiCls : "bg-brand-bar")}
                style={{ height: `${Math.max(6, Math.round(b * 144))}px` }}
              />
            </div>
          ))}
        </div>
      </div>
      <div className="mt-2 flex items-center justify-between">
        <span className="text-faint text-[12px] leading-[15px] font-medium">{axisStart}</span>
        <span className="text-ink text-[12px] leading-[15px] font-semibold">{axisEnd}</span>
      </div>
      {footnote ? <Footnote className="mt-[14px]">{footnote}</Footnote> : null}
    </div>
  );
}

/** Progress steps on a phone: five 5px bars. */
export function StepBars({ done, total }: { done: number; total: number }) {
  return (
    <div className="mt-4 flex gap-[6px]">
      {Array.from({ length: total }, (_, i) => (
        <span
          key={i}
          className={cn("h-[5px] flex-1 rounded-[3px]", i < done ? "bg-brand" : "bg-[#dbe2e8]")}
        />
      ))}
    </div>
  );
}

/* ---------- The strip above the headline (a notice, a support view, a viewer) ---------- */
export function Banner({
  tone = "amber",
  tag,
  text,
  link,
  actions,
}: {
  tone?: "amber" | "brand";
  tag: string;
  text: string;
  link?: { label: string; href?: string };
  actions?: ReactNode;
}) {
  return (
    <div
      className={cn(
        "mb-[26px] flex flex-wrap items-center gap-x-3 gap-y-2 rounded-[12px] border px-[15px] py-[11px]",
        tone === "amber" ? "bg-amber-tint border-amber-line" : "border-[#d6def3] bg-[#eef2fb]",
      )}
    >
      <span
        className={cn(
          "inline-flex h-[23px] items-center rounded-full px-[10px] text-[12px] leading-[15px] font-semibold",
          tone === "amber" ? "bg-amber-pale text-amber-dark" : "text-brand bg-[#dde5f8]",
        )}
      >
        {tag}
      </span>
      <p className="text-ink min-w-0 flex-1 text-[14px] leading-[17px] font-medium">{text}</p>
      {link ? (
        <Link
          href={link.href ?? "#"}
          className="text-brand text-[14px] leading-[17px] font-semibold"
        >
          {link.label}
        </Link>
      ) : null}
      {actions}
    </div>
  );
}

/** A 10px swatch and a word at the right of a panel header. */
export function Legend({
  label,
  tone = "brand",
}: {
  label: string;
  tone?: "brand" | "red" | "amber";
}) {
  return (
    <span className="text-muted flex shrink-0 items-center gap-2 text-[13px] leading-4 font-medium">
      <span
        aria-hidden
        className={cn(
          "size-[10px] rounded-[3px]",
          { brand: "bg-brand", red: "bg-red-strong", amber: "bg-amber" }[tone],
        )}
      />
      {label}
    </span>
  );
}

/** The small 14-bar chart used for days: heights 0 to 1, with tone per bar. */
export function MiniBars({
  bars,
  labels,
  height = 80,
}: {
  bars: { h: number; tone?: "soft" | "brand" | "empty" | "red" }[];
  /** Three labels: start, middle (bold), end. */
  labels: [string, string?, string?];
  height?: number;
}) {
  return (
    <div className="mt-[18px]">
      <div className="flex items-end gap-[10px]" style={{ height }}>
        {bars.map((b, i) => (
          <span
            key={i}
            className={cn(
              "block flex-1 rounded-[4px]",
              {
                soft: "bg-brand-bar",
                brand: "bg-brand",
                empty: "bg-line-soft",
                red: "bg-red-pale",
              }[b.tone ?? "soft"],
            )}
            style={{ height: `${Math.max(4, Math.round(b.h * height))}px` }}
          />
        ))}
      </div>
      <div className="mt-2 flex items-center justify-between text-[12px] leading-[15px]">
        <span className="text-faint font-medium">{labels[0]}</span>
        {labels[1] ? <span className="text-ink font-semibold">{labels[1]}</span> : null}
        {labels[2] ? <span className="text-faint font-medium">{labels[2]}</span> : null}
      </div>
    </div>
  );
}

/** A 19/23 sentence followed by a 15/18 muted paragraph, for "What Google said". */
export function Quote({ said, then, note }: { said: string; then?: string; note?: string }) {
  return (
    <>
      <Summary>{said}</Summary>
      {then ? <p className="text-muted mt-[18px] text-[15px] leading-[18px]">{then}</p> : null}
      {note ? <Footnote className="mt-[18px]">{note}</Footnote> : null}
    </>
  );
}

/* ---------- Form-style blocks drawn on the settings and editor frames ---------- */
/** A radio option card: 12px radius, brand border and pale fill when selected. */
export function Choice({
  title,
  meta,
  selected,
  chip,
  chipTone = "pale",
  disabled,
  name,
}: {
  title: string;
  meta?: ReactNode;
  selected?: boolean;
  chip?: string;
  chipTone?: ChipTone;
  disabled?: boolean;
  name?: string;
}) {
  return (
    <label
      className={cn(
        "mt-[10px] flex cursor-pointer items-start gap-[14px] rounded-[12px] border px-[17px] py-4 first:mt-[18px]",
        selected ? "border-brand bg-brand-tint" : "border-line bg-panel hover:bg-line-soft",
        disabled && "cursor-default",
      )}
    >
      <input
        type="radio"
        name={name}
        defaultChecked={selected}
        disabled={disabled}
        className="peer sr-only"
      />
      <span
        aria-hidden
        className={cn(
          "mt-[1px] flex size-5 shrink-0 items-center justify-center rounded-full border bg-white",
          selected ? "border-brand" : "border-[#b8c3cc]",
        )}
      >
        {selected ? <span className="bg-brand block size-[10px] rounded-full" /> : null}
      </span>
      <span className="min-w-0 flex-1">
        <span
          className={cn(
            "block text-[15px] leading-[18px] font-semibold",
            disabled ? "text-faint" : "text-ink",
          )}
        >
          {title}
        </span>
        {meta ? (
          <span
            className={cn(
              "mt-1 block text-[14px] leading-[17px]",
              disabled ? "text-faint" : "text-muted",
            )}
          >
            {meta}
          </span>
        ) : null}
      </span>
      {chip ? <StatusPill tone={chipTone}>{chip}</StatusPill> : null}
    </label>
  );
}

/** A labelled 44px input as drawn in the panels: 13/600 muted label, hairline border. */
export function FieldRow({
  label,
  value,
  placeholder,
  suffix,
  type = "text",
  select,
}: {
  label: string;
  value?: string;
  placeholder?: string;
  suffix?: string;
  type?: string;
  select?: boolean;
}) {
  return (
    <label className="mt-[18px] block">
      <span className="text-muted block text-[13px] leading-4 font-semibold">{label}</span>
      <span className="border-line bg-panel mt-[7px] flex h-11 items-center rounded-[12px] border px-[15px]">
        <input
          type={type}
          defaultValue={value}
          placeholder={placeholder}
          className="text-ink placeholder:text-faint w-full bg-transparent text-[15px] leading-[18px] outline-none"
        />
        {suffix ? (
          <span className="text-faint shrink-0 text-[14px] leading-[17px] font-medium">
            {suffix}
          </span>
        ) : null}
        {select ? (
          <span aria-hidden className="text-faint shrink-0 text-[14px]">
            ▾
          </span>
        ) : null}
      </span>
    </label>
  );
}

/** A numbered step: 28px brand-pale circle, a title and a meta line. */
export function Step({
  n,
  title,
  meta,
  tone = "brand",
}: {
  n: number;
  title: string;
  meta: string;
  tone?: "brand" | "grey" | "amber" | "red";
}) {
  return (
    <li className="flex items-start gap-[14px] py-[10px]">
      <span
        className={cn(
          "flex size-7 shrink-0 items-center justify-center rounded-full text-[13px] leading-4 font-bold",
          {
            brand: "bg-brand-pale text-brand-dark",
            grey: "bg-line-soft text-muted",
            amber: "bg-amber-pale text-amber-dark",
            red: "bg-red-pale text-red",
          }[tone],
        )}
      >
        {n}
      </span>
      <span className="min-w-0">
        <span className="text-ink block text-[15px] leading-[18px] font-semibold">{title}</span>
        <span className="text-muted mt-[3px] block text-[14px] leading-[17px]">{meta}</span>
      </span>
    </li>
  );
}

/** A labelled 8px meter: "Good" on the left, "4 headlines" on the right. */
export function Meter({
  name,
  value,
  fill,
  tone = "brand",
}: {
  name: string;
  value?: string;
  fill: number;
  tone?: "brand" | "amber" | "red";
}) {
  return (
    <div className="mt-[18px]">
      <div className="flex items-center justify-between text-[14px] leading-[17px]">
        <span className="text-ink font-medium">{name}</span>
        {value ? <span className="text-ink font-semibold">{value}</span> : null}
      </div>
      <div className="bg-track mt-2 h-2 overflow-hidden rounded-full">
        <div
          className={cn(
            "h-full rounded-full",
            { brand: "bg-brand", amber: "bg-amber", red: "bg-red-strong" }[tone],
          )}
          style={{ width: `${Math.round(fill * 100)}%` }}
        />
      </div>
    </div>
  );
}

/** The amber "ready" panel at the foot of an aside: a title, a line, two buttons. */
export function ActionPanel({
  title,
  body,
  primary,
  secondary,
  disabled,
  tone = "amber",
  primaryTone,
}: {
  title: string;
  body: ReactNode;
  primary: string;
  secondary?: string;
  /** The primary is drawn grey with a reason nearby. */
  disabled?: boolean;
  tone?: "amber" | "panel" | "red";
  primaryTone?: "brand" | "red" | "ink";
}) {
  return (
    <NoticeCard
      tone={tone}
      compact
      title={title}
      body={body}
      primary={{ label: primary }}
      primaryTone={disabled ? "secondary" : primaryTone}
      secondary={secondary ? { label: secondary } : undefined}
    />
  );
}

/** The dark pill row: "All" selected, the others grey, used as a filter. */
export function FilterChips({ options, active }: { options: string[]; active: string }) {
  return (
    <div className="mt-[10px] flex flex-wrap gap-[6px]">
      {options.map((o) => (
        <button
          key={o}
          type="button"
          className={cn(
            "h-[23px] rounded-full px-[10px] text-[12px] leading-[15px] font-semibold",
            o === active
              ? "bg-brand-pale text-brand-dark"
              : "bg-line-soft text-muted hover:text-ink",
          )}
        >
          {o}
        </button>
      ))}
    </div>
  );
}

/** A row with a title, meta, and a text link on the right (Remove, Read, Report). */
export function LinkRow({
  title,
  meta,
  link,
  tone = "brand",
}: {
  title: ReactNode;
  meta?: ReactNode;
  link: string;
  tone?: "brand" | "muted" | "red";
}) {
  return (
    <ListRow
      title={title}
      meta={meta}
      right={
        <button
          type="button"
          className={cn(
            "shrink-0 text-[14px] leading-[17px] font-semibold",
            { brand: "text-brand", muted: "text-muted", red: "text-red-strong" }[tone],
          )}
        >
          {link}
        </button>
      }
    />
  );
}

/** Image placeholders as drawn on the Performance Max frames: tinted blocks with a caption or a rating. */
export function Gallery({
  items,
  square,
}: {
  items: { tint: string; caption?: string; chip?: string; chipTone?: ChipTone; empty?: boolean }[];
  square?: boolean;
}) {
  return (
    <div
      className={cn(
        "mt-4 grid gap-3",
        square ? "grid-cols-3 sm:grid-cols-4 lg:grid-cols-6" : "grid-cols-2 sm:grid-cols-4",
      )}
    >
      {items.map((it, i) => (
        <figure key={i} className="min-w-0">
          {it.empty ? (
            <div className="bg-ad-bg text-faint flex aspect-square items-center justify-center rounded-[10px] border border-[#cfd8e0] text-[13px] font-semibold">
              + Add
            </div>
          ) : (
            <div
              className={cn("w-full rounded-[10px]", square ? "aspect-square" : "aspect-[156/82]")}
              style={{ background: it.tint }}
            />
          )}
          {it.caption || it.chip ? (
            <figcaption className="mt-[6px] flex flex-wrap items-center gap-[6px]">
              {it.chip ? <StatusPill tone={it.chipTone ?? "pale"}>{it.chip}</StatusPill> : null}
              {it.caption ? (
                <span className="text-faint text-[12px] leading-[15px]">{it.caption}</span>
              ) : null}
            </figcaption>
          ) : null}
        </figure>
      ))}
    </div>
  );
}

/** The dashed drop zone from the logo panel. */
export function DropZone({ title, meta, button }: { title: string; meta: string; button: string }) {
  return (
    <div className="bg-ad-bg mt-3 flex flex-col items-center rounded-[12px] border border-dashed border-[#b8c3cc] px-5 py-[22px] text-center">
      <p className="text-ink text-[15px] leading-[18px] font-semibold">{title}</p>
      <p className="text-faint mt-2 text-[13px] leading-4">{meta}</p>
      <Button variant="secondary" size="sm" className="border-line mt-[14px] h-11">
        {button}
      </Button>
    </div>
  );
}

/** A row where the right side is a bold value instead of a pill. */
export function ValueRow({
  title,
  meta,
  value,
}: {
  title: ReactNode;
  meta?: ReactNode;
  value: string;
}) {
  return (
    <ListRow
      title={title}
      meta={meta}
      right={
        <span className="text-ink shrink-0 text-[15px] leading-[18px] font-semibold">{value}</span>
      }
    />
  );
}

/** The 40x24 switch, brand when on. Static until the backend drives it. */
export function Toggle({ on, label }: { on: boolean; label?: string }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={on}
      aria-label={label}
      className={cn(
        "relative inline-block h-6 w-10 shrink-0 rounded-full transition-colors",
        on ? "bg-brand" : "bg-[#cfd8e0]",
      )}
    >
      <span
        className={cn(
          "absolute top-[3px] size-[18px] rounded-full bg-white transition-[left]",
          on ? "left-[19px]" : "left-[3px]",
        )}
      />
    </button>
  );
}

/** A row with one or two toggles on the right, for the notification choices. */
export function ToggleRow({
  title,
  meta,
  toggles,
}: {
  title: string;
  meta?: string;
  toggles: boolean[];
}) {
  return (
    <ListRow
      title={title}
      meta={meta}
      right={
        <span className="flex shrink-0 gap-7">
          {toggles.map((t, i) => (
            <Toggle key={i} on={t} label={`${title} ${i === 0 ? "in app" : "by email"}`} />
          ))}
        </span>
      }
    />
  );
}

/** The "Reason, required" box inside an admin notice card. */
export function ReasonInput({
  value,
  placeholder,
  tone = "amber",
}: {
  value?: string;
  placeholder?: string;
  tone?: "amber" | "line";
}) {
  return (
    <label
      className={cn(
        "mt-3 block rounded-[12px] border bg-white px-[15px] py-[13px]",
        tone === "amber" ? "border-[#e6cea4]" : "border-line",
      )}
    >
      <span
        className={cn(
          "block text-[12px] leading-[15px] font-semibold",
          tone === "amber" ? "text-amber-dark" : "text-muted",
        )}
      >
        Reason, required
      </span>
      <input
        defaultValue={value}
        placeholder={placeholder}
        className="text-ink placeholder:text-faint mt-1 w-full bg-transparent text-[14px] leading-[17px] outline-none"
      />
    </label>
  );
}
