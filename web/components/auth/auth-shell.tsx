import Image from "next/image";
import Link from "next/link";
import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

/*
  The way in, wearing the dashboard's own skin: the night panel on the left with
  the wordmark and the pitch, the warm ground on the right holding a 460px card.

  The client's handoff does not draw these screens — it covers the signed-in app
  and says to use its shell and tokens for anything it missed. So they use them,
  and somebody signing in and landing on the dashboard sees one product rather
  than two.
*/
export function AuthShell({
  headline,
  body,
  footnote,
  children,
  below,
  brand = "ppcway",
}: {
  headline: string;
  body: string;
  footnote?: ReactNode;
  children: ReactNode;
  /** The line under the card, such as "New to PPCWay? Create an account". */
  below?: ReactNode;
  /** The wordmark; an agency's clients see the agency's name. */
  brand?: string;
}) {
  return (
    // `site` carries the client's brand blue, which the shared buttons read.
    <div className="site bg-pw-ground text-pw-ink flex min-h-dvh flex-col lg:flex-row">
      <aside className="bg-pw-night text-pw-night-text lg:flex lg:w-[540px] lg:shrink-0 lg:flex-col lg:justify-between">
        <div className="px-6 pt-8 pb-8 sm:px-10 lg:px-14 lg:pt-14 lg:pb-0">
          <Link href="/" className="inline-flex items-center">
            <Image
              src="/brand/ppcway-logo-white.svg"
              alt={brand === "ppcway" ? "PPCway" : brand}
              width={140}
              height={30}
              priority
              className="h-[30px] w-auto"
            />
          </Link>
        </div>
        <div className="px-6 pb-10 sm:px-10 lg:px-14 lg:pb-0">
          <h1 className="display max-w-[428px] text-[26px] leading-[32px] font-semibold text-balance sm:text-[32px] sm:leading-[39px]">
            {headline}
          </h1>
          <p className="text-pw-night-muted mt-[18px] max-w-[440px] text-[16px] leading-[24px]">
            {body}
          </p>
        </div>
        {footnote ? (
          <p className="text-pw-ink-300 hidden px-14 pb-14 text-[14px] leading-[20px] lg:block">
            {footnote}
          </p>
        ) : null}
      </aside>

      <main className="flex flex-1 flex-col items-center justify-center px-4 py-10 sm:px-8 lg:py-16">
        <div className="w-full max-w-[460px]">{children}</div>
        {below ? (
          <p className="text-pw-ink-500 mt-5 text-center text-[14px] leading-[20px]">{below}</p>
        ) : null}
        {footnote ? (
          <p className="text-pw-ink-400 mt-8 text-center text-[13px] leading-[19px] lg:hidden">
            {footnote}
          </p>
        ) : null}
      </main>
    </div>
  );
}

export function AuthCard({
  title,
  intro,
  children,
  className,
  onSubmit,
}: {
  title: string;
  /** The muted line under the title, such as "or use your email" or the code explanation. */
  intro?: ReactNode;
  children?: ReactNode;
  className?: string;
  onSubmit?: (event: React.FormEvent<HTMLFormElement>) => void;
}) {
  const Tag = onSubmit ? "form" : "section";
  return (
    <Tag
      onSubmit={onSubmit}
      noValidate={onSubmit ? true : undefined}
      className={cn(
        "bg-pw-card border-pw-border flex flex-col gap-[18px] rounded-[18px] border p-6 sm:p-10",
        className,
      )}
    >
      <h2 className="display text-[26px] leading-[31px] font-semibold">{title}</h2>
      {intro ? (
        <div className="text-pw-ink-400 -mt-2 text-[13px] leading-4 font-medium">{intro}</div>
      ) : null}
      {children}
    </Tag>
  );
}
