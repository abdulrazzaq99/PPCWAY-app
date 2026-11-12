"use client";

import { DesktopIcon, DeviceMobileIcon, ImageIcon, ShuffleIcon } from "@phosphor-icons/react";
import { useState, type ReactNode } from "react";
import { cn } from "@/lib/cn";
import type { AdImage, AdText, Pin, Sitelink, Spec } from "@/lib/creation";
import { domainOf, Segmented } from "./b-form";
import { CTA_LABEL } from "./b-options";

/*
  What the ad may look like. Google assembles a responsive ad itself, for
  each search, from the lines it was given: up to three headlines and two
  descriptions, pinned lines always in their place. This draws one such
  combination and "Shuffle" draws another, all in the browser. It is a
  preview of how Google may combine them, not a promise of what shows.
*/

/** The same order for the same seed, so a preview does not jump on every keystroke. */
function shuffled<T>(items: T[], seed: number): T[] {
  if (!seed) return items;
  const out = [...items];
  // mulberry32: small, fast, and the same sequence for the same seed.
  let s = seed >>> 0;
  const next = () => {
    s = (s + 0x6d2b79f5) | 0;
    let t = Math.imul(s ^ (s >>> 15), 1 | s);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  for (let i = out.length - 1; i > 0; i -= 1) {
    const j = Math.floor(next() * (i + 1));
    [out[i], out[j]] = [out[j], out[i]];
  }
  return out;
}

/** One line per position: a pinned line where there is one, the next free line otherwise. */
export function combine(lines: AdText[], positions: Pin[], seed: number): string[] {
  const live = lines.filter((l) => l.text.trim());
  const free = shuffled(
    live.filter((l) => !l.pin),
    seed,
  );
  const out: string[] = [];
  for (const position of positions) {
    const pinned = live.filter((l) => l.pin === position);
    if (pinned.length) out.push(pinned[seed % pinned.length].text.trim());
    else {
      const next = free.shift();
      if (next) out.push(next.text.trim());
    }
  }
  return out;
}

type Device = "mobile" | "desktop";

const DEVICES = [
  { value: "mobile" as const, label: "Mobile", icon: <DeviceMobileIcon className="size-[14px]" /> },
  { value: "desktop" as const, label: "Desktop", icon: <DesktopIcon className="size-[14px]" /> },
];

function Frame({ device, children }: { device: Device; children: ReactNode }) {
  return (
    <div
      className={cn(
        "border-pw-border bg-pw-card mx-auto w-full border p-4",
        device === "mobile" ? "max-w-[380px] rounded-[22px]" : "rounded-[12px]",
      )}
    >
      {children}
    </div>
  );
}

function Shuffle({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="text-pw-blue hover:bg-pw-blue-tint inline-flex items-center gap-1 rounded-full px-3 py-[5px] text-[12px] font-semibold"
    >
      <ShuffleIcon className="size-[14px]" /> Shuffle
    </button>
  );
}

/** The ad as a Google search result: Sponsored, who, where, then the words. */
function TextResult({
  device,
  business,
  shownUrl,
  headlines,
  descriptions,
  sitelinks = [],
  callouts = [],
}: {
  device: Device;
  business: string;
  shownUrl: string;
  headlines: string[];
  descriptions: string[];
  sitelinks?: string[];
  callouts?: string[];
}) {
  const initial = (business || shownUrl).trim().charAt(0).toUpperCase() || "G";
  return (
    <div className="flex min-w-0 flex-col gap-1">
      <p className="text-pw-ink text-[12px] font-bold">Sponsored</p>
      <div className="flex items-center gap-2">
        <span
          aria-hidden
          className="bg-pw-muted text-pw-ink-600 flex size-[26px] shrink-0 items-center justify-center rounded-full text-[12px] font-semibold"
        >
          {initial}
        </span>
        <span className="flex min-w-0 flex-col leading-[16px]">
          <span className="text-pw-ink truncate text-[13px]">{business || "Your business"}</span>
          <span className="text-pw-ink-500 truncate text-[12px]">{shownUrl}</span>
        </span>
      </div>
      <p
        className={cn(
          "text-pw-blue mt-1 break-words",
          device === "mobile" ? "text-[17px] leading-[22px]" : "text-[19px] leading-[25px]",
        )}
      >
        {headlines.length ? headlines.join(" | ") : "Your headlines show here"}
      </p>
      <p className="text-pw-ink-700 text-[13px] leading-[19px] break-words">
        {descriptions.length ? descriptions.join(" ") : "Your descriptions show here."}
      </p>
      {callouts.length ? (
        <p className="text-pw-ink-600 text-[13px] leading-[19px]">{callouts.join(" · ")}</p>
      ) : null}
      {sitelinks.length >= 2 ? (
        <div
          className={cn(
            "mt-1 gap-x-4 gap-y-1",
            device === "mobile" ? "flex flex-wrap" : "grid grid-cols-2",
          )}
        >
          {sitelinks.slice(0, device === "mobile" ? 4 : 4).map((s) => (
            <span key={s} className="text-pw-blue truncate text-[14px]">
              {s}
            </span>
          ))}
        </div>
      ) : null}
    </div>
  );
}

export function SearchPreview({
  headlines,
  descriptions,
  url,
  path1,
  path2,
  business,
  sitelinks,
  callouts,
}: {
  headlines: AdText[];
  descriptions: AdText[];
  url: string;
  path1: string;
  path2: string;
  business: string;
  sitelinks: Sitelink[];
  callouts: string[];
}) {
  const [device, setDevice] = useState<Device>("mobile");
  const [seed, setSeed] = useState(0);
  const shownUrl = [domainOf(url) || "example.com", path1.trim(), path1.trim() ? path2.trim() : ""]
    .filter(Boolean)
    .join("/");
  return (
    <section aria-label="Ad preview" className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h4 className="text-pw-ink text-[14px] font-semibold">Preview</h4>
        <div className="flex items-center gap-1">
          <Segmented label="Preview on" value={device} options={DEVICES} onChange={setDevice} />
          <Shuffle onClick={() => setSeed((s) => s + 1)} />
        </div>
      </div>
      <Frame device={device}>
        <TextResult
          device={device}
          business={business}
          shownUrl={shownUrl}
          headlines={combine(headlines, ["HEADLINE_1", "HEADLINE_2", "HEADLINE_3"], seed)}
          descriptions={combine(descriptions, ["DESCRIPTION_1", "DESCRIPTION_2"], seed)}
          sitelinks={sitelinks.map((s) => s.text.trim()).filter(Boolean)}
          callouts={callouts
            .map((c) => c.trim())
            .filter(Boolean)
            .slice(0, 4)}
        />
      </Frame>
      <p className="text-pw-ink-500 text-[12px] leading-[17px]">
        A preview of how Google may combine your headlines and descriptions. Google picks the
        combination for each search, and may show two headlines instead of three.
      </p>
    </section>
  );
}

type Group = Spec["pmax"]["asset_group"];
type Format = "search" | "display" | "discover";

const FORMATS = [
  { value: "search" as const, label: "Search" },
  { value: "display" as const, label: "Display" },
  { value: "discover" as const, label: "Discover" },
];

function Picture({ image, ratio }: { image?: AdImage; ratio: number }) {
  return (
    <div
      className="bg-pw-muted flex w-full items-center justify-center overflow-hidden"
      style={{ aspectRatio: String(ratio) }}
    >
      {image?.url ? (
        // Google's own hosted copy of the asset.
        // eslint-disable-next-line @next/next/no-img-element
        <img src={image.url} alt="" className="size-full object-cover" />
      ) : (
        <ImageIcon className="text-pw-ink-300 size-8" aria-label="No image yet" />
      )}
    </div>
  );
}

/** Two or three of the places a Performance Max ad shows, drawn from the asset group. */
export function PmaxPreview({ group, business }: { group: Group; business: string }) {
  const [format, setFormat] = useState<Format>("display");
  const [seed, setSeed] = useState(0);
  const pick = <T,>(items: T[]): T | undefined =>
    items.length ? items[seed % items.length] : undefined;
  const heads = group.headlines.map((h) => h.trim()).filter(Boolean);
  const longs = group.long_headlines.map((h) => h.trim()).filter(Boolean);
  const descs = group.descriptions.map((d) => d.trim()).filter(Boolean);
  const cta = CTA_LABEL[group.call_to_action] ?? "Learn more";
  const shownUrl = [
    domainOf(group.final_url) || "example.com",
    group.path1.trim(),
    group.path1.trim() ? group.path2.trim() : "",
  ]
    .filter(Boolean)
    .join("/");
  const logo = group.logos[0];
  return (
    <section aria-label="Asset group preview" className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h4 className="text-pw-ink text-[14px] font-semibold">Preview</h4>
        <div className="flex items-center gap-1">
          <Segmented label="Show as" value={format} options={FORMATS} onChange={setFormat} />
          <Shuffle onClick={() => setSeed((s) => s + 1)} />
        </div>
      </div>
      <Frame device="mobile">
        {format === "search" ? (
          <TextResult
            device="mobile"
            business={business}
            shownUrl={shownUrl}
            headlines={shuffled(heads, seed).slice(0, 3)}
            descriptions={shuffled(descs, seed).slice(0, 1)}
          />
        ) : format === "display" ? (
          <div className="border-pw-border overflow-hidden rounded-[10px] border">
            <Picture image={pick(group.marketing_images)} ratio={1.91} />
            <div className="flex flex-col gap-1 p-3">
              <p className="text-pw-ink text-[15px] leading-[20px] font-semibold">
                {pick(heads) ?? "Your headline"}
              </p>
              <p className="text-pw-ink-600 text-[13px] leading-[18px]">
                {pick(descs) ?? "Your description."}
              </p>
              <div className="mt-2 flex items-center justify-between gap-2">
                <span className="flex min-w-0 items-center gap-2">
                  {logo?.url ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={logo.url} alt="" className="size-6 rounded-full object-cover" />
                  ) : null}
                  <span className="text-pw-ink-600 truncate text-[12px]">
                    {business || "Your business"}
                  </span>
                </span>
                <span className="bg-pw-blue shrink-0 rounded-full px-3 py-[5px] text-[12px] font-semibold text-white">
                  {cta}
                </span>
              </div>
            </div>
          </div>
        ) : (
          <div className="flex flex-col gap-2">
            <div className="overflow-hidden rounded-[10px]">
              <Picture image={pick(group.square_images)} ratio={1} />
            </div>
            <p className="text-pw-ink text-[15px] leading-[20px] font-semibold">
              {pick(longs) ?? pick(heads) ?? "Your long headline"}
            </p>
            <p className="text-pw-ink-500 text-[12px]">
              <span className="text-pw-ink font-bold">Sponsored</span> ·{" "}
              {business || "Your business"}
            </p>
          </div>
        )}
      </Frame>
      <p className="text-pw-ink-500 text-[12px] leading-[17px]">
        A preview of how Google may put your assets together. Performance Max builds ads for Search,
        YouTube, Display, Discover, Gmail and Maps, and chooses the mix itself.
      </p>
    </section>
  );
}
