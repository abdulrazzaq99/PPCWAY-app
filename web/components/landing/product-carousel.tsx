"use client";

import { useEffect, useState, type ReactNode } from "react";
import { cn } from "@/lib/cn";

/*
  The hero preview: four real product cards on a turntable. The front card faces
  you; the previous and next ones are turned away on either side, further back,
  faded and slightly out of focus, so the eye reads depth rather than a stack.
  Every few seconds the table turns one place: the front card swings out to the
  left, the right card swings in. Hovering or focusing the frame stops the clock.
  Under reduced motion the cards cross-fade in place.
*/
export type Slide = { name: string; card: ReactNode };

const EVERY = 3200;

/*
  The turntable needs room either side for the neighbours to stand in. It has
  that from `lg` up, where the frame bleeds past the column and a gradient mask
  softens where they leave — see the section's own classes.

  Below that there is no room and no mask, so a neighbour at translateX(50%)
  does not stand beside the front card, it stands on it: two cards legible at
  once, 70% opacity each, which on a phone reads as a rendering fault rather
  than as depth. So the neighbours only appear where they fit. Narrower than
  that, the cards cross-fade in place, which is what reduced motion already
  does and what the eye expects of one card at a time.
*/
const POSITIONS: Record<string, string> = {
  "0": "z-20 opacity-100 lg:[transform:perspective(1400px)_translateX(0)_translateZ(0)_rotateY(0)]",
  "-1": "z-10 opacity-0 lg:opacity-70 lg:blur-[1.5px] lg:[transform:perspective(1400px)_translateX(-46%)_translateZ(-240px)_rotateY(36deg)]",
  "1": "z-10 opacity-0 lg:opacity-70 lg:blur-[1.5px] lg:[transform:perspective(1400px)_translateX(50%)_translateZ(-240px)_rotateY(-36deg)]",
  "2": "z-0 opacity-0 lg:blur-[3px] lg:[transform:perspective(1400px)_translateX(0)_translateZ(-420px)_rotateY(0)]",
};

export function ProductCarousel({ slides, label }: { slides: Slide[]; label: string }) {
  const [index, setIndex] = useState(0);
  const [held, setHeld] = useState(false);
  const [still, setStill] = useState(false);
  const n = slides.length;

  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const apply = () => setStill(mq.matches);
    apply();
    mq.addEventListener("change", apply);
    return () => mq.removeEventListener("change", apply);
  }, []);

  useEffect(() => {
    if (held || still) return;
    const t = window.setInterval(() => {
      if (document.visibilityState === "visible") setIndex((i) => (i + 1) % n);
    }, EVERY);
    return () => window.clearInterval(t);
  }, [held, still, n]);

  /** Where a slide sits relative to the front one: -1 left, 0 front, 1 right, 2 back. */
  function place(i: number) {
    const d = (i - index + n) % n;
    if (d === 0) return "0";
    if (d === 1) return "1";
    if (d === n - 1) return "-1";
    return "2";
  }

  return (
    <section
      aria-roledescription="carousel"
      aria-label={label}
      onMouseEnter={() => setHeld(true)}
      onMouseLeave={() => setHeld(false)}
      onFocus={() => setHeld(true)}
      onBlur={() => setHeld(false)}
      className="-my-20 grid items-stretch py-20 [transform-style:preserve-3d] lg:-mr-80 lg:-ml-16 lg:[mask-image:linear-gradient(to_right,transparent,black_64px)] lg:pr-80 lg:pl-16"
    >
      {slides.map((s, i) => {
        const at = place(i);
        const active = at === "0";
        return (
          <div
            key={s.name}
            role="group"
            aria-roledescription="slide"
            aria-label={`${i + 1} of ${n}: ${s.name}`}
            aria-hidden={!active}
            inert={!active}
            className={cn(
              "transition-[opacity,transform,filter] duration-[900ms] ease-[cubic-bezier(0.22,1,0.36,1)] will-change-transform [grid-area:1/1]",
              still ? (active ? "z-20 opacity-100" : "z-0 opacity-0") : POSITIONS[at],
              !active && "pointer-events-none",
            )}
          >
            {s.card}
          </div>
        );
      })}
    </section>
  );
}
