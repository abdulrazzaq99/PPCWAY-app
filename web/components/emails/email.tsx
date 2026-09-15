import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

/*
  Every email PPCWay sends, from the "V2 · Email" frames: a 600px white card with
  the wordmark and a date, a 24/30 headline, one sentence, up to three stat boxes,
  a short list with coloured dots, and one action card with one button.
*/
export type Stat = { label: string; value: string; tone?: "brand" | "red" | "amber" | "grey" };
export type EmailSpec = {
  caption: string;
  brand?: string;
  date: string;
  headline: string;
  sentence: string;
  stats?: Stat[];
  section?: string;
  items?: string[];
  dot?: "brand" | "red" | "amber" | "grey";
  action?: {
    text: string;
    button?: string;
    tone?: "brand" | "red" | "ink";
    skip?: string;
    box?: "amber" | "red" | "brand" | "grey";
  };
  footer?: string;
};

const statTones = {
  brand: "bg-brand-pale text-brand-dark",
  red: "bg-red-pale text-red",
  amber: "bg-amber-tint text-amber-dark",
  grey: "bg-canvas text-ink",
};
const dotTones = { brand: "bg-brand", red: "bg-red-strong", amber: "bg-amber", grey: "bg-faint" };
const boxTones = {
  amber: "bg-amber-tint border border-amber-line",
  red: "bg-red-pale border border-[#f2d4d3]",
  brand: "bg-brand-pale",
  grey: "bg-[#f7f9fb]",
};

export function Email({ spec }: { spec: EmailSpec }) {
  const s = spec;
  const box = s.action?.box ?? "grey";
  return (
    <figure className="min-w-0">
      <figcaption className="text-muted text-[14px] leading-[17px] font-semibold">
        {s.caption}
      </figcaption>
      <article className="bg-panel border-line mt-3 rounded-[16px] border px-6 py-8 sm:px-10">
        <header className="flex items-center justify-between gap-4">
          <span className="flex items-center gap-2">
            <span className="bg-brand inline-block size-6 rounded-[7px]" />
            <span className="text-ink text-[18px] leading-[22px] font-bold">
              {s.brand ?? "ppcway"}
            </span>
          </span>
          <span className="text-faint text-[13px] leading-4 font-medium">{s.date}</span>
        </header>
        <h2 className="text-ink mt-5 text-[24px] leading-[30px] font-semibold text-balance">
          {s.headline}
        </h2>
        <p className="text-muted mt-4 text-[15px] leading-[18px]">{s.sentence}</p>
        {s.stats ? (
          <div
            className={cn("mt-5 grid gap-3", s.stats.length === 2 ? "grid-cols-2" : "grid-cols-3")}
          >
            {s.stats.map((st) => (
              <div
                key={st.label}
                className={cn("rounded-[12px] px-4 py-[14px]", statTones[st.tone ?? "grey"])}
              >
                <p
                  className={cn(
                    "text-[12px] leading-[15px] font-medium",
                    st.tone && st.tone !== "grey" ? "" : "text-muted",
                  )}
                >
                  {st.label}
                </p>
                <p className="mt-1 text-[22px] leading-[27px] font-semibold">{st.value}</p>
              </div>
            ))}
          </div>
        ) : null}
        {s.section ? (
          <p className="text-ink mt-5 text-[15px] leading-[18px] font-semibold">{s.section}</p>
        ) : null}
        {s.items ? (
          <ul className="mt-4 flex flex-col gap-[18px]">
            {s.items.map((it) => (
              <li key={it} className="flex items-start gap-[10px]">
                <span
                  className={cn(
                    "mt-[5px] size-2 shrink-0 rounded-full",
                    dotTones[s.dot ?? "brand"],
                  )}
                />
                <span className="text-ink text-[14px] leading-[17px]">{it}</span>
              </li>
            ))}
          </ul>
        ) : null}
        {s.action ? (
          <div className={cn("mt-6 rounded-[12px] px-5 py-5", boxTones[box])}>
            <p className="text-ink text-[15px] leading-[18px] font-medium">{s.action.text}</p>
            {s.action.button ? (
              <button
                type="button"
                className={cn(
                  "mt-4 h-[42px] rounded-full px-5 text-[15px] font-semibold text-white",
                  s.action.tone === "red"
                    ? "bg-red-strong"
                    : s.action.tone === "ink"
                      ? "bg-rail"
                      : "bg-brand",
                )}
              >
                {s.action.button}
              </button>
            ) : null}
            {s.action.skip ? (
              <p className="text-amber-dark mt-3 text-[14px] leading-[17px] font-semibold">
                {s.action.skip}
              </p>
            ) : null}
          </div>
        ) : null}
        {s.footer ? <p className="text-faint mt-5 text-[12px] leading-[15px]">{s.footer}</p> : null}
      </article>
    </figure>
  );
}

export function EmailGallery({
  title,
  lead,
  emails,
  children,
}: {
  title: string;
  lead: string;
  emails: EmailSpec[];
  children?: ReactNode;
}) {
  return (
    <section className="mx-auto max-w-[1280px] px-5 py-10 sm:px-10 lg:py-14">
      <h1 className="text-ink text-[28px] leading-[34px] font-semibold lg:text-[32px] lg:leading-[39px]">
        {title}
      </h1>
      <p className="text-muted mt-3 max-w-[1000px] text-[17px] leading-[21px]">{lead}</p>
      {children}
      <div className="mt-8 grid gap-8 lg:grid-cols-2">
        {emails.map((e) => (
          <Email key={e.caption + e.headline} spec={e} />
        ))}
      </div>
    </section>
  );
}
