"use client";

import { useEffect, useState } from "react";
import { LinkButton } from "@/components/ui/button";
import { cn } from "@/lib/cn";

/*
  The bar that follows the reader down the report. It arrives once the score has
  scrolled away and steps aside while the closing section is on screen, so the page
  never asks twice at once. Nothing in it is invented: the sentence is the report's
  own cost, per day.
*/
export function FixBar({ text, closeId = "close" }: { text: string; closeId?: string }) {
  const [past, setPast] = useState(false);
  const [atClose, setAtClose] = useState(false);

  useEffect(() => {
    const onScroll = () => setPast(window.scrollY > 480);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    const close = document.getElementById(closeId);
    const watch = close
      ? new IntersectionObserver(([entry]) => setAtClose(entry.isIntersecting))
      : null;
    if (close && watch) watch.observe(close);
    return () => {
      window.removeEventListener("scroll", onScroll);
      watch?.disconnect();
    };
  }, [closeId]);

  const shown = past && !atClose;
  return (
    <div
      aria-hidden={!shown}
      inert={!shown}
      className={cn(
        "fixed inset-x-0 bottom-0 z-30 px-4 pb-[calc(16px+env(safe-area-inset-bottom,0px))]",
        "transition-transform duration-300 ease-out motion-reduce:transition-none",
        shown ? "translate-y-0" : "translate-y-[140%]",
      )}
    >
      <div className="bg-ink mx-auto flex max-w-[960px] flex-col gap-3 rounded-[16px] px-5 py-4 text-white shadow-[0_30px_70px_-30px_rgba(15,23,32,0.6)] sm:flex-row sm:items-center sm:justify-between sm:gap-6">
        <p className="text-[14px] leading-[18px] font-semibold sm:text-[15px] sm:leading-5">
          {text}
        </p>
        <LinkButton href="/signup" size="sm" className="w-full shrink-0 sm:w-auto">
          Fix these for me
        </LinkButton>
      </div>
    </div>
  );
}
