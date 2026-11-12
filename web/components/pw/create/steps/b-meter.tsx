"use client";

import { cn } from "@/lib/cn";
import type { Label, Rating } from "./b-strength";

/*
  The Ad Strength meter, in Google's shape: a bar that fills by label and the
  label in words, then what would raise it. Said plainly to be PPCWay's
  estimate, because Google rates the ad itself only after it is published.
*/
const STEPS: Exclude<Label, "Incomplete">[] = ["Poor", "Average", "Good", "Excellent"];

const TONE: Record<Label, { text: string; bar: string }> = {
  Incomplete: { text: "text-pw-ink-500", bar: "bg-pw-ink-300" },
  Poor: { text: "text-pw-bad", bar: "bg-pw-bad-solid" },
  Average: { text: "text-pw-warn-ink", bar: "bg-pw-warn" },
  Good: { text: "text-pw-blue-ink", bar: "bg-pw-blue" },
  Excellent: { text: "text-pw-good-ink", bar: "bg-pw-good-solid" },
};

export function StrengthMeter({
  rating,
  title = "Ad strength",
  note,
}: {
  rating: Rating;
  title?: string;
  note?: string;
}) {
  const reached = rating.label === "Incomplete" ? 0 : STEPS.indexOf(rating.label) + 1;
  const tone = TONE[rating.label];
  return (
    <section
      aria-label={`${title}: ${rating.label}`}
      className="border-pw-border bg-pw-card flex flex-col gap-3 rounded-[14px] border p-4"
    >
      <div className="flex items-baseline justify-between gap-3">
        <h4 className="text-pw-ink text-[14px] font-semibold">{title}</h4>
        <span className={cn("text-[15px] font-semibold", tone.text)}>{rating.label}</span>
      </div>
      <div className="grid grid-cols-4 gap-1" aria-hidden>
        {STEPS.map((step, at) => (
          <span
            key={step}
            className={cn("h-[6px] rounded-full", at < reached ? tone.bar : "bg-pw-track")}
          />
        ))}
      </div>
      <p className="text-pw-ink-500 text-[12px] leading-[17px]">
        {note ??
          "PPCWay's estimate of Google's Ad Strength, from the factors Google publishes. Google shows its own rating once the ad is published. It does not change what you pay or where the ad shows."}
      </p>
      {rating.fixes.length ? (
        <div className="flex flex-col gap-1">
          <p className="text-pw-ink text-[13px] font-semibold">
            {rating.label === "Incomplete" ? "Needed before it can be rated" : "How to improve"}
          </p>
          <ul className="text-pw-ink-700 flex list-disc flex-col gap-1 pl-5 text-[13px] leading-[18px]">
            {rating.fixes.slice(0, 5).map((fix) => (
              <li key={fix}>{fix}</li>
            ))}
          </ul>
        </div>
      ) : (
        <p className="text-pw-good-ink text-[13px]">Nothing more to add.</p>
      )}
    </section>
  );
}
