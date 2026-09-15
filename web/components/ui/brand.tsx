import Link from "next/link";
import { cn } from "@/lib/cn";

/*
  The wordmark: a 28px rounded brand square and "ppcway" in Inter Bold 21.
  On a dark surface the wordmark is white; on a light one it is ink.
*/
export function Brand({
  tone = "dark",
  size = 28,
  href,
  name = "ppcway",
  className,
}: {
  tone?: "dark" | "light";
  size?: 26 | 28;
  href?: string;
  name?: string;
  className?: string;
}) {
  const inner = (
    <span className={cn("inline-flex items-center gap-[10px]", className)}>
      <span
        aria-hidden
        className="bg-brand inline-block shrink-0"
        style={{ width: size, height: size, borderRadius: size === 28 ? 9 : 8 }}
      />
      <span
        className={cn(
          "font-bold tracking-[-0.01em]",
          size === 28 ? "text-[21px] leading-[25px]" : "text-[19px] leading-[23px]",
          tone === "dark" ? "text-white" : "text-ink",
        )}
      >
        {name}
      </span>
    </span>
  );
  if (!href) return inner;
  return (
    <Link
      href={href}
      aria-label={`${name} home`}
      className="focus-visible:ring-brand-bar inline-flex rounded-sm focus-visible:ring-4 focus-visible:outline-none"
    >
      {inner}
    </Link>
  );
}

/** The four-square mark drawn beside "Continue with Google" in the file. */
export function GoogleMark({ className }: { className?: string }) {
  return (
    <span aria-hidden className={cn("grid size-[18px] grid-cols-2 gap-[2px]", className)}>
      <span className="rounded-[2px] bg-[#4285f4]" />
      <span className="rounded-[2px] bg-[#ea4335]" />
      <span className="rounded-[2px] bg-[#fbbc05]" />
      <span className="rounded-[2px] bg-[#34a853]" />
    </span>
  );
}
