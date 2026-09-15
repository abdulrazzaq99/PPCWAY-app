import type { ReactNode } from "react";
import { Brand } from "@/components/ui/brand";
import { TextLink } from "@/components/ui/button";
import { cn } from "@/lib/cn";

/*
  The two "V2 Error" frames share this shape: a light top bar with the wordmark and a
  Help centre link, a 600px column in the middle with an icon chip, a code line, a 40px
  headline, a body and two buttons, and a quiet footer line at the foot.
*/
export function ProblemPage({
  tone,
  icon,
  code,
  headline,
  body,
  actions,
  footer,
}: {
  tone: "brand" | "amber";
  icon: ReactNode;
  code: string;
  headline: string;
  body: string;
  actions: ReactNode;
  footer: string;
}) {
  return (
    <div className="flex min-h-dvh flex-col px-6 py-10 sm:px-14">
      <header className="flex items-center justify-between">
        <Brand tone="light" href="/" />
        <TextLink href="/help">Help centre</TextLink>
      </header>

      <main className="flex flex-1 items-center justify-center py-16">
        <div className="w-full max-w-[600px]">
          <span
            className={cn(
              "flex size-14 items-center justify-center rounded-[16px]",
              tone === "brand" ? "bg-brand-pale" : "bg-amber-tint border-amber-line border",
            )}
          >
            {icon}
          </span>
          <p
            className={cn(
              "mt-[18px] text-[14px] leading-[17px] font-semibold",
              tone === "brand" ? "text-brand" : "text-amber",
            )}
          >
            {code}
          </p>
          <h1 className="text-ink mt-[18px] text-[32px] leading-[39px] font-semibold text-balance sm:text-[40px] sm:leading-[48px]">
            {headline}
          </h1>
          <p className="text-subline mt-[18px]">{body}</p>
          <div className="mt-[18px] flex flex-wrap gap-3 pt-2">{actions}</div>
        </div>
      </main>

      <footer className="text-faint text-[13px] leading-4">{footer}</footer>
    </div>
  );
}

export function SearchGlyph() {
  return (
    <span aria-hidden className="relative block size-6">
      <span className="border-brand absolute inset-0 rounded-full border-2" />
      <span className="bg-brand absolute -right-[4px] -bottom-[3px] h-1 w-[11px] rotate-45 rounded-[2px]" />
    </span>
  );
}

export function ExclamationGlyph() {
  return (
    <span aria-hidden className="flex flex-col items-center gap-[5px]">
      <span className="bg-amber block h-[17px] w-[5px] rounded-[3px]" />
      <span className="bg-amber block size-[5px] rounded-[3px]" />
    </span>
  );
}
