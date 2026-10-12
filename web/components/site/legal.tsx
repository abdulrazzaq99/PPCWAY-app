import Link from "next/link";
import type { ReactNode } from "react";
import { Brand } from "@/components/ui/brand";

/*
  The shell the legal pages wear: the public site's chrome, nothing clever. These
  pages have to be readable by a plumber and by Google's reviewer, and reachable
  without signing in, which is a condition of the Google verification they exist
  to satisfy.
*/
export function LegalPage({
  title,
  updated,
  lede,
  children,
}: {
  title: string;
  updated: string;
  lede: string;
  children: ReactNode;
}) {
  return (
    <div className="site bg-canvas text-ink min-h-screen">
      <header className="mx-auto flex max-w-[1200px] items-center justify-between px-5 py-6 sm:px-8">
        <Brand tone="light" size={26} href="/" />
        <nav className="text-muted flex gap-x-6 text-[14px]" aria-label="Site">
          <Link href="/audit" className="hover:text-ink">
            Free audit
          </Link>
          <Link href="/login" className="hover:text-ink">
            Sign in
          </Link>
        </nav>
      </header>

      <main className="mx-auto max-w-[760px] px-5 pt-6 pb-20 sm:px-8">
        <h1 className="text-[34px] leading-[42px] font-semibold sm:text-[44px] sm:leading-[52px]">
          {title}
        </h1>
        <p className="text-muted mt-4 text-[17px] leading-[27px]">{lede}</p>
        <p className="text-faint mt-3 text-[14px]">Last updated {updated}</p>
        <div className="legal mt-10">{children}</div>
      </main>

      <footer className="border-line-soft mx-auto flex max-w-[1200px] flex-wrap items-center justify-between gap-4 border-t px-5 py-8 sm:px-8">
        <p className="text-faint text-[13px] leading-4">PPCWay · Mississauga, Ontario</p>
        <nav className="text-muted flex flex-wrap gap-x-6 gap-y-2 text-[14px]" aria-label="Legal">
          <Link href="/privacy" className="hover:text-ink">
            Privacy
          </Link>
          <Link href="/terms" className="hover:text-ink">
            Terms
          </Link>
          <Link href="/help" className="hover:text-ink">
            Help
          </Link>
        </nav>
      </footer>
    </div>
  );
}

export function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="mt-9 first:mt-0">
      <h2 className="text-[22px] leading-[28px] font-semibold">{title}</h2>
      <div className="mt-3 flex flex-col gap-3 text-[16px] leading-[26px]">{children}</div>
    </section>
  );
}

export function Rule({ children }: { children: ReactNode }) {
  return <ul className="border-line-soft divide-line-soft mt-1 divide-y border-t">{children}</ul>;
}

export function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <li className="grid gap-1 py-3 sm:grid-cols-[200px_1fr] sm:gap-5">
      <span className="text-[15px] leading-[22px] font-semibold">{label}</span>
      <span className="text-muted text-[15px] leading-[23px]">{children}</span>
    </li>
  );
}
