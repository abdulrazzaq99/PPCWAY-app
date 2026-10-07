import Link from "next/link";
import type { ReactNode } from "react";
import { Brand } from "@/components/ui/brand";
import { cn } from "@/lib/cn";

/*
  The public audit screens, now in the client's website design: their warm ground,
  their blue, Outfit over DM Sans, and the deeper radii their cards use. The `site`
  class carries that palette (see globals.css); the signed-in app keeps Version 2.
*/
export function AuditNav({ left }: { left?: ReactNode }) {
  return (
    <header className="bg-panel">
      <div className="border-line-soft mx-auto flex h-[76px] max-w-[1200px] items-center justify-between border-b px-5">
        <Brand tone="light" size={26} href="/" />
        <div className="flex items-center gap-4">
          {left ?? (
            <Link href="/login" className="text-ink text-[15px] leading-[18px] font-semibold">
              Log in
            </Link>
          )}
          <Link
            href="/signup"
            className="bg-brand hover:bg-brand-dark inline-flex h-[42px] items-center rounded-[12px] px-5 text-[15px] font-semibold text-white"
          >
            Free instant audit
          </Link>
        </div>
      </div>
    </header>
  );
}

export function AuditPage({
  children,
  wide,
  navLeft,
}: {
  children: ReactNode;
  wide?: boolean;
  navLeft?: ReactNode;
}) {
  return (
    <div className="site bg-canvas text-ink min-h-dvh">
      <AuditNav left={navLeft} />
      <main
        className={cn(
          "mx-auto px-5 pt-12 pb-20 sm:px-8 lg:pt-16",
          wide ? "max-w-[1200px]" : "max-w-[860px]",
        )}
      >
        {children}
      </main>
    </div>
  );
}

export function Card({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div
      className={cn(
        "bg-panel border-line rounded-[22px] border shadow-[0_30px_60px_-40px_rgba(43,31,102,0.22)]",
        className,
      )}
    >
      {children}
    </div>
  );
}

export function Pill({
  children,
  tone = "brand",
}: {
  children: ReactNode;
  tone?: "brand" | "grey" | "amber";
}) {
  return (
    <span
      className={cn(
        "inline-flex h-[23px] items-center rounded-full px-[10px] text-[12px] leading-[15px] font-semibold",
        tone === "brand" && "bg-brand-pale text-brand-dark",
        tone === "grey" && "bg-line-soft text-muted",
        tone === "amber" && "bg-amber-pale text-amber-dark",
      )}
    >
      {children}
    </span>
  );
}
