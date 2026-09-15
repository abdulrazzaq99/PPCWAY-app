import type { ReactNode } from "react";
import { Brand } from "@/components/ui/brand";
import { cn } from "@/lib/cn";

/*
  The sign-in family, from the "V2 Log in" frames.
  Desktop: a 540px navy panel on the left with the wordmark at the top, a pitch in the
  middle and a footnote at the foot; the canvas on the right holds a 460px card.
  Narrow screens: the navy panel becomes a band across the top with the wordmark and
  the pitch, and the card fills the width below it.
*/
export function AuthShell({
  headline,
  body,
  footnote,
  children,
  below,
}: {
  headline: string;
  body: string;
  footnote?: ReactNode;
  children: ReactNode;
  /** The line under the card, such as "New to PPCWay? Create an account". */
  below?: ReactNode;
}) {
  return (
    <div className="flex min-h-dvh flex-col lg:flex-row">
      <aside className="bg-rail text-white lg:flex lg:w-[540px] lg:shrink-0 lg:flex-col lg:justify-between">
        <div className="px-6 pt-8 pb-8 sm:px-10 lg:px-14 lg:pt-14 lg:pb-0">
          <Brand tone="dark" href="/" />
        </div>
        <div className="px-6 pb-10 sm:px-10 lg:px-14 lg:pb-0">
          <h1 className="max-w-[428px] text-[26px] leading-[32px] font-semibold text-balance sm:text-[32px] sm:leading-[39px]">
            {headline}
          </h1>
          <p className="text-rail-icon mt-[18px] max-w-[440px] text-[16px] leading-[19px]">
            {body}
          </p>
        </div>
        {footnote ? (
          <p className="text-rail-text hidden px-14 pb-14 text-[14px] leading-[17px] lg:block">
            {footnote}
          </p>
        ) : null}
      </aside>

      <main className="flex flex-1 flex-col items-center justify-center px-4 py-10 sm:px-8 lg:py-16">
        <div className="w-full max-w-[460px]">{children}</div>
        {below ? (
          <p className="text-muted mt-5 text-center text-[14px] leading-[17px]">{below}</p>
        ) : null}
        {footnote ? (
          <p className="text-faint mt-8 text-center text-[13px] leading-4 lg:hidden">{footnote}</p>
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
        "bg-panel border-line flex flex-col gap-[18px] rounded-[20px] border p-6 sm:p-10",
        className,
      )}
    >
      <h2 className="text-ink text-[26px] leading-[31px] font-semibold">{title}</h2>
      {intro ? (
        <div className="text-faint -mt-2 text-[13px] leading-4 font-medium">{intro}</div>
      ) : null}
      {children}
    </Tag>
  );
}
