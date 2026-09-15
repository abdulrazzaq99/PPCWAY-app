"use client";

import { useEffect, useRef, type ReactNode } from "react";
import { cn } from "@/lib/cn";

/*
  Scroll reveal for the landing page: a section fades and lifts 16px into place the
  first time it enters the viewport. Motion is hierarchy, not decoration: it draws the
  eye to the section that just arrived. IntersectionObserver only, no scroll listeners,
  and nothing moves under prefers-reduced-motion (globals.css zeroes the durations).
*/
export function Reveal({
  children,
  className,
  delay = 0,
}: {
  children: ReactNode;
  className?: string;
  delay?: number;
}) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      el.dataset.shown = "true";
      return;
    }
    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (e.isIntersecting) {
            el.dataset.shown = "true";
            io.disconnect();
          }
        }
      },
      { threshold: 0.2 },
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);
  return (
    <div
      ref={ref}
      style={{ transitionDelay: `${delay}ms` }}
      className={cn(
        "translate-y-4 opacity-0 transition-[opacity,transform] duration-[600ms] ease-[cubic-bezier(0.16,1,0.3,1)] data-[shown=true]:translate-y-0 data-[shown=true]:opacity-100",
        className,
      )}
    >
      {children}
    </div>
  );
}
