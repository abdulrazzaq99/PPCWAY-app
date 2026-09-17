import Link from "next/link";
import type { ReactNode } from "react";
import { Brand } from "@/components/ui/brand";
import { cn } from "@/lib/cn";

/*
  The public audit screens, from the "V2 · Audit" frames: a white 87px bar with the
  wordmark, Log in and a Start free pill, then a 760px column on the canvas.
  The frames are drawn in emerald; the app is blue, so these use the brand tokens.
*/
export function AuditNav({ left }: { left?: ReactNode }) {
  return (
    <header className="bg-panel">
      <div className="border-line-soft mx-auto flex h-[87px] max-w-[1296px] items-center justify-between border-b px-5 sm:px-0">
        <Brand tone="light" size={26} href="/" />
        <div className="flex items-center gap-4">
          {left ?? (
            <Link href="/login" className="text-ink text-[15px] leading-[18px] font-semibold">
              Log in
            </Link>
          )}
          <Link
            href="/signup"
            className="bg-brand hover:bg-brand-dark inline-flex h-[42px] items-center rounded-full px-5 text-[15px] font-semibold text-white"
          >
            Start free
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
    <div className="bg-canvas text-ink min-h-dvh">
      <AuditNav left={navLeft} />
      <main
        className={cn(
          "mx-auto px-5 pt-12 pb-20 sm:px-8 lg:pt-16",
          wide ? "max-w-[1296px]" : "max-w-[760px]",
        )}
      >
        {children}
      </main>
    </div>
  );
}

export function Card({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={cn("bg-panel border-line rounded-[16px] border", className)}>{children}</div>
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
