"use client";

import {
  CaretDownIcon,
  CheckCircleIcon,
  ImageSquareIcon,
  InfoIcon,
  PushPinIcon,
  TrashIcon,
  WarningCircleIcon,
  XIcon,
} from "@phosphor-icons/react";
import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/field";
import { cn } from "@/lib/cn";
import { call, said, type AdImage, type Pin, type Problem } from "@/lib/creation";

/*
  The controls every creation step is built from, in the shape Google's own
  creation screens use: a setting is a row with its name on the left and a
  one-line summary of the choice, opened to change it; switches, radio
  choices with a line of help each, text boxes that count characters against
  Google's limit as you type. Brand colours and radii are PPCWay's.
*/

/** A titled card holding one group of settings, as Google groups them. */
export function Card({
  title,
  help,
  children,
  aside,
  className,
}: {
  title?: string;
  help?: ReactNode;
  children: ReactNode;
  aside?: ReactNode;
  className?: string;
}) {
  return (
    <section className={cn("bg-pw-card border-pw-border rounded-[18px] border", className)}>
      {title ? (
        <header className="border-pw-border flex items-start justify-between gap-4 border-b px-6 py-4">
          <div>
            <h2 className="text-pw-ink text-[17px] leading-[22px] font-semibold">{title}</h2>
            {help ? (
              <p className="text-pw-ink-500 mt-1 text-[13px] leading-[18px]">{help}</p>
            ) : null}
          </div>
          {aside}
        </header>
      ) : null}
      <div className="flex flex-col">{children}</div>
    </section>
  );
}

/*
  One setting: name on the left, the current choice in a line beside it, and
  the controls underneath when opened. Google's "Networks", "Locations",
  "Ad schedule" rows are all this shape.
*/
export function Panel({
  title,
  summary,
  children,
  open: startOpen = false,
  flagged,
}: {
  title: string;
  summary: ReactNode;
  children: ReactNode;
  open?: boolean;
  /** A problem on this setting: the row says so even when closed. */
  flagged?: boolean;
}) {
  const [open, setOpen] = useState(startOpen);
  const id = useId();
  return (
    <div className="border-pw-border border-b last:border-b-0">
      <button
        type="button"
        aria-expanded={open}
        aria-controls={id}
        onClick={() => setOpen((o) => !o)}
        className="hover:bg-pw-row-hover flex w-full items-start gap-4 px-6 py-4 text-left transition-colors"
      >
        <span className="text-pw-ink w-[180px] shrink-0 text-[14px] leading-[20px] font-semibold">
          {title}
        </span>
        <span className="text-pw-ink-600 min-w-0 flex-1 text-[14px] leading-[20px]">
          {flagged ? (
            <WarningCircleIcon
              weight="fill"
              className="text-pw-bad mr-1 inline size-4 align-[-3px]"
              aria-label="Needs attention"
            />
          ) : null}
          {summary}
        </span>
        <CaretDownIcon
          className={cn(
            "text-pw-ink-400 mt-[2px] size-4 shrink-0 transition-transform",
            open && "rotate-180",
          )}
        />
      </button>
      {open ? (
        <div id={id} className="flex flex-col gap-4 px-6 pt-1 pb-5 sm:pl-[220px]">
          {children}
        </div>
      ) : null}
    </div>
  );
}

/** An on/off switch with its label. */
export function Toggle({
  on,
  onChange,
  children,
  help,
  disabled,
}: {
  on: boolean;
  onChange: (next: boolean) => void;
  children: ReactNode;
  help?: ReactNode;
  disabled?: boolean;
}) {
  return (
    <label
      className={cn(
        "flex cursor-pointer items-start gap-3",
        disabled && "cursor-not-allowed opacity-60",
      )}
    >
      <button
        type="button"
        role="switch"
        aria-checked={on}
        disabled={disabled}
        onClick={() => onChange(!on)}
        className={cn(
          "relative mt-[1px] h-[22px] w-[38px] shrink-0 rounded-full transition-colors",
          "focus-visible:ring-brand-bar focus-visible:ring-4 focus-visible:outline-none",
          on ? "bg-pw-blue" : "bg-pw-border-strong",
        )}
      >
        <span
          className={cn(
            "absolute top-[3px] left-[3px] size-4 rounded-full bg-white shadow transition-transform",
            on && "translate-x-4",
          )}
        />
      </button>
      <span className="flex flex-col gap-[2px]">
        <span className="text-pw-ink text-[14px] leading-[20px] font-medium">{children}</span>
        {help ? <span className="text-pw-ink-500 text-[13px] leading-[18px]">{help}</span> : null}
      </span>
    </label>
  );
}

/** One radio choice with a line of help, as Google words its options. */
export function Choice({
  name,
  checked,
  onChange,
  children,
  help,
  disabled,
}: {
  name: string;
  checked: boolean;
  onChange: () => void;
  children: ReactNode;
  help?: ReactNode;
  disabled?: boolean;
}) {
  const id = useId();
  return (
    <label
      htmlFor={id}
      className={cn(
        "flex cursor-pointer items-start gap-3",
        disabled && "cursor-not-allowed opacity-60",
      )}
    >
      <input
        id={id}
        type="radio"
        name={name}
        checked={checked}
        disabled={disabled}
        onChange={onChange}
        className="accent-pw-blue mt-[3px] size-4 shrink-0"
      />
      <span className="flex flex-col gap-[2px]">
        <span className="text-pw-ink text-[14px] leading-[20px] font-medium">{children}</span>
        {help ? <span className="text-pw-ink-500 text-[13px] leading-[18px]">{help}</span> : null}
      </span>
    </label>
  );
}

/** A checkbox with its label and help line. */
export function Tick({
  checked,
  onChange,
  children,
  help,
  disabled,
}: {
  checked: boolean;
  onChange: (next: boolean) => void;
  children: ReactNode;
  help?: ReactNode;
  disabled?: boolean;
}) {
  const id = useId();
  return (
    <label
      htmlFor={id}
      className={cn(
        "flex cursor-pointer items-start gap-3",
        disabled && "cursor-not-allowed opacity-60",
      )}
    >
      <input
        id={id}
        type="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={(e) => onChange(e.target.checked)}
        className="accent-pw-blue mt-[3px] size-4 shrink-0"
      />
      <span className="flex flex-col gap-[2px]">
        <span className="text-pw-ink text-[14px] leading-[20px] font-medium">{children}</span>
        {help ? <span className="text-pw-ink-500 text-[13px] leading-[18px]">{help}</span> : null}
      </span>
    </label>
  );
}

/** A labelled control, smaller than `Field`, for dense settings. */
export function Labelled({
  label,
  hint,
  children,
  className,
}: {
  label: string;
  hint?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-col gap-[6px]", className)}>
      <span className="text-pw-ink text-[13px] leading-[18px] font-semibold">{label}</span>
      {children}
      {hint ? <span className="text-pw-ink-500 text-[12px] leading-[16px]">{hint}</span> : null}
    </div>
  );
}

/** A number box. Empty is null, which is not the same as zero. */
export function NumberBox({
  value,
  onChange,
  unit,
  placeholder,
  min,
  max,
  step,
  className,
  ariaLabel,
}: {
  value: number | null;
  onChange: (next: number | null) => void;
  unit?: string;
  placeholder?: string;
  min?: number;
  max?: number;
  step?: number;
  className?: string;
  ariaLabel?: string;
}) {
  return (
    <Input
      type="number"
      inputMode="decimal"
      aria-label={ariaLabel}
      value={value ?? ""}
      min={min}
      max={max}
      step={step ?? "any"}
      placeholder={placeholder}
      onChange={(e) => onChange(e.target.value === "" ? null : Number(e.target.value))}
      trailing={unit ? <span className="text-pw-ink-400 text-[13px]">{unit}</span> : null}
      className={className}
    />
  );
}

/** A text box that counts characters against Google's limit, as Google's editor does. */
export function Counted({
  value,
  onChange,
  most,
  placeholder,
  ariaLabel,
  className,
  trailing,
}: {
  value: string;
  onChange: (next: string) => void;
  most: number;
  placeholder?: string;
  ariaLabel?: string;
  className?: string;
  trailing?: ReactNode;
}) {
  const over = value.length > most;
  return (
    <div className={cn("relative", className)}>
      <Input
        value={value}
        aria-label={ariaLabel}
        invalid={over}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        trailing={
          <span className="flex items-center gap-2">
            {trailing}
            <span
              className={cn("text-[12px] tabular-nums", over ? "text-pw-bad" : "text-pw-ink-400")}
            >
              {value.length}/{most}
            </span>
          </span>
        }
      />
    </div>
  );
}

/*
  A list of lines, each counted: headlines, descriptions, callouts, search
  themes. Empty lines stay while the merchant types; the server ignores them.
*/
export function Lines({
  values,
  onChange,
  most,
  longest,
  placeholder,
  addLabel,
  pins,
  pinned,
  onPin,
  least,
}: {
  values: string[];
  onChange: (next: string[]) => void;
  most: number;
  longest: number;
  placeholder: string;
  addLabel: string;
  /** Pin positions offered for each line, as Google's responsive search ad editor has them. */
  pins?: Pin[];
  pinned?: (Pin | null)[];
  onPin?: (at: number, pin: Pin | null) => void;
  least?: number;
}) {
  const filled = values.filter((v) => v.trim()).length;
  return (
    <div className="flex flex-col gap-2">
      {values.map((value, at) => (
        <div key={at} className="flex items-center gap-2">
          <Counted
            value={value}
            most={longest}
            placeholder={`${placeholder} ${at + 1}`}
            ariaLabel={`${placeholder} ${at + 1}`}
            onChange={(next) => onChange(values.map((v, i) => (i === at ? next : v)))}
            className="flex-1"
            trailing={
              pins && pinned?.[at] ? (
                <span className="bg-pw-blue-tint text-pw-blue-ink rounded-full px-2 text-[11px] font-semibold">
                  Pinned {pinned[at]!.replace("HEADLINE_", "H").replace("DESCRIPTION_", "D")}
                </span>
              ) : null
            }
          />
          {pins && onPin ? (
            <PinMenu pins={pins} value={pinned?.[at] ?? null} onChange={(p) => onPin(at, p)} />
          ) : null}
          <button
            type="button"
            aria-label={`Remove ${placeholder.toLowerCase()} ${at + 1}`}
            onClick={() => onChange(values.filter((_, i) => i !== at))}
            className="text-pw-ink-400 hover:text-pw-bad hover:bg-pw-muted rounded-full p-2"
          >
            <TrashIcon className="size-4" />
          </button>
        </div>
      ))}
      <div className="flex items-center justify-between gap-3">
        <button
          type="button"
          disabled={values.length >= most}
          onClick={() => onChange([...values, ""])}
          className="text-pw-blue disabled:text-pw-ink-300 self-start text-[14px] font-semibold"
        >
          + {addLabel}
        </button>
        <span className="text-pw-ink-400 text-[12px]">
          {filled} of {most}
          {least ? `, at least ${least}` : ""}
        </span>
      </div>
    </div>
  );
}

function PinMenu({
  pins,
  value,
  onChange,
}: {
  pins: Pin[];
  value: Pin | null;
  onChange: (next: Pin | null) => void;
}) {
  const label = (p: Pin) =>
    p.startsWith("HEADLINE_")
      ? `Pin to headline position ${p.slice(-1)}`
      : `Pin to description position ${p.slice(-1)}`;
  return (
    <label className="relative">
      <span className="sr-only">Pin</span>
      <PushPinIcon
        weight={value ? "fill" : "regular"}
        className={cn(
          "pointer-events-none absolute top-1/2 left-2 size-4 -translate-y-1/2",
          value ? "text-pw-blue" : "text-pw-ink-400",
        )}
      />
      <select
        value={value ?? ""}
        onChange={(e) => onChange((e.target.value || null) as Pin | null)}
        className="border-pw-border-input text-pw-ink h-[46px] w-[46px] cursor-pointer appearance-none rounded-[12px] border bg-transparent pl-8 text-[0px]"
        title={value ? label(value) : "Pin"}
      >
        <option value="">Don&apos;t pin</option>
        {pins.map((p) => (
          <option key={p} value={p}>
            {label(p)}
          </option>
        ))}
      </select>
    </label>
  );
}

/** Words added one at a time, shown as chips. */
export function Chips({
  values,
  onChange,
  placeholder,
  most,
  longest,
  ariaLabel,
}: {
  values: string[];
  onChange: (next: string[]) => void;
  placeholder: string;
  most?: number;
  longest?: number;
  ariaLabel?: string;
}) {
  const [typed, setTyped] = useState("");
  const full = most !== undefined && values.length >= most;
  const add = () => {
    const parts = typed
      .split(/\n|,/)
      .map((p) => p.trim())
      .filter(Boolean)
      .map((p) => (longest ? p.slice(0, longest) : p));
    const next = [...values];
    for (const p of parts) {
      if (most !== undefined && next.length >= most) break;
      if (!next.some((v) => v.toLowerCase() === p.toLowerCase())) next.push(p);
    }
    onChange(next);
    setTyped("");
  };
  return (
    <div className="flex flex-col gap-2">
      <div className="flex gap-2">
        <Input
          value={typed}
          aria-label={ariaLabel ?? placeholder}
          disabled={full}
          placeholder={full ? "That is as many as Google allows" : placeholder}
          onChange={(e) => setTyped(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              add();
            }
          }}
          className="flex-1"
        />
        <Button variant="secondary" size="sm" onClick={add} disabled={!typed.trim() || full}>
          Add
        </Button>
      </div>
      {values.length ? (
        <div className="flex flex-wrap gap-2">
          {values.map((v) => (
            <Pill key={v} onRemove={() => onChange(values.filter((x) => x !== v))}>
              {v}
            </Pill>
          ))}
        </div>
      ) : null}
    </div>
  );
}

export function Pill({
  children,
  onRemove,
  tone = "blue",
}: {
  children: ReactNode;
  onRemove?: () => void;
  tone?: "blue" | "red";
}) {
  return (
    <span
      className={cn(
        "inline-flex max-w-full items-center gap-1 rounded-full py-[5px] pr-1 pl-3 text-[13px] font-semibold",
        tone === "red" ? "bg-pw-bad-bg text-pw-bad-ink" : "bg-pw-blue-tint text-pw-blue-ink",
        !onRemove && "pr-3",
      )}
    >
      <span className="truncate">{children}</span>
      {onRemove ? (
        <button
          type="button"
          onClick={onRemove}
          aria-label="Remove"
          className="hover:bg-pw-card rounded-full p-1"
        >
          <XIcon className="size-3" />
        </button>
      ) : null}
    </span>
  );
}

/*
  A search box that asks the server as the merchant types and lets them pick
  from what comes back: places, audiences, brands.
*/
export function Finder<T>({
  path,
  pick,
  render,
  keyOf,
  placeholder,
  ariaLabel,
  least = 2,
  onPick,
  empty = "Nothing found.",
}: {
  path: (q: string) => string | null;
  pick: (data: unknown) => T[];
  render: (item: T) => ReactNode;
  keyOf: (item: T) => string;
  placeholder: string;
  ariaLabel?: string;
  least?: number;
  onPick: (item: T) => void;
  empty?: string;
}) {
  const [typed, setTyped] = useState("");
  const [found, setFound] = useState<T[] | null>(null);
  const [looking, setLooking] = useState(false);
  const [trouble, setTrouble] = useState("");

  useEffect(() => {
    const q = typed.trim();
    const where = q.length >= least ? path(q) : null;
    if (!where) return;
    let live = true;
    const timer = setTimeout(async () => {
      setLooking(true);
      const { ok, data } = await call<unknown>(where);
      if (!live) return;
      setLooking(false);
      setTrouble(ok ? "" : said(data, "Google could not be asked just now."));
      setFound(ok ? pick(data) : []);
    }, 300);
    return () => {
      live = false;
      clearTimeout(timer);
    };
    // `path` and `pick` are written inline by callers; the text is what matters.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [typed, least]);

  const shown = typed.trim().length >= least ? found : null;
  return (
    <div className="flex flex-col gap-2">
      <Input
        value={typed}
        aria-label={ariaLabel ?? placeholder}
        placeholder={placeholder}
        onChange={(e) => setTyped(e.target.value)}
        trailing={looking ? <span className="text-pw-ink-400 text-[13px]">Looking…</span> : null}
      />
      {trouble ? <p className="text-pw-bad text-[13px]">{trouble}</p> : null}
      {shown && !looking ? (
        shown.length ? (
          <ul className="border-pw-border divide-pw-border max-h-[280px] divide-y overflow-y-auto rounded-[12px] border">
            {shown.map((item) => (
              <li key={keyOf(item)}>
                <button
                  type="button"
                  className="hover:bg-pw-muted flex w-full items-center justify-between gap-3 px-4 py-[10px] text-left text-[14px]"
                  onClick={() => {
                    onPick(item);
                    setTyped("");
                    setFound(null);
                  }}
                >
                  {render(item)}
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-pw-ink-500 text-[13px]">{empty}</p>
        )
      ) : null}
    </div>
  );
}

/** A short note in the flow: Google's advice, or why something is not offered. */
export function Note({
  tone = "info",
  children,
  className,
}: {
  tone?: "info" | "warn" | "good" | "bad";
  children: ReactNode;
  className?: string;
}) {
  const Icon = tone === "good" ? CheckCircleIcon : tone === "info" ? InfoIcon : WarningCircleIcon;
  return (
    <div
      className={cn(
        "flex items-start gap-3 rounded-[12px] px-4 py-3 text-[13px] leading-[19px]",
        tone === "info" && "bg-pw-blue-tint text-pw-blue-ink",
        tone === "warn" && "bg-pw-warn-bg text-pw-warn-ink",
        tone === "good" && "bg-pw-good-bg text-pw-good-ink",
        tone === "bad" && "bg-pw-bad-bg text-pw-bad-ink",
        className,
      )}
    >
      <Icon weight="fill" className="mt-[1px] size-4 shrink-0" />
      <div className="min-w-0">{children}</div>
    </div>
  );
}

/** What is stopping this step, in a list, as Google's left menu flags it. */
export function Problems({ items }: { items: Problem[] }) {
  if (!items.length) return null;
  const blocking = items.filter((p) => p.blocks);
  const advice = items.filter((p) => !p.blocks);
  return (
    <div className="flex flex-col gap-2">
      {blocking.length ? (
        <Note tone="bad">
          <ul className="flex flex-col gap-1">
            {blocking.map((p, i) => (
              <li key={i}>{p.words}</li>
            ))}
          </ul>
        </Note>
      ) : null}
      {advice.length ? (
        <Note tone="warn">
          <ul className="flex flex-col gap-1">
            {advice.map((p, i) => (
              <li key={i}>{p.words}</li>
            ))}
          </ul>
        </Note>
      ) : null}
    </div>
  );
}

/*
  Images, the way Google's asset picker takes them: choose a file, it is cut
  to the shape Google needs (centred, as Google's crop starts), scaled to
  Google's recommended size, and added to the account's asset library
  straight away. What comes back is an image the campaign can link.
*/
export type Shape = "landscape" | "square" | "portrait" | "logo" | "landscape_logo";

export const SHAPES: Record<
  Shape,
  { label: string; ratio: number; width: number; height: number; least: string }
> = {
  landscape: {
    label: "Landscape (1.91:1)",
    ratio: 1.91,
    width: 1200,
    height: 628,
    least: "600 × 314",
  },
  square: { label: "Square (1:1)", ratio: 1, width: 1200, height: 1200, least: "300 × 300" },
  portrait: { label: "Portrait (4:5)", ratio: 0.8, width: 960, height: 1200, least: "480 × 600" },
  logo: { label: "Square logo (1:1)", ratio: 1, width: 1200, height: 1200, least: "128 × 128" },
  landscape_logo: {
    label: "Landscape logo (4:1)",
    ratio: 4,
    width: 1200,
    height: 300,
    least: "512 × 128",
  },
};

async function cropped(file: File, shape: Shape): Promise<{ data: string; small: boolean }> {
  const url = URL.createObjectURL(file);
  try {
    const img = await new Promise<HTMLImageElement>((resolve, reject) => {
      const el = new Image();
      el.onload = () => resolve(el);
      el.onerror = () => reject(new Error("That file is not an image a browser can read."));
      el.src = url;
    });
    const target = SHAPES[shape];
    const srcRatio = img.naturalWidth / img.naturalHeight;
    let sw = img.naturalWidth;
    let sh = img.naturalHeight;
    // An image already in Google's shape is kept whole: 1200 x 628 is 1.9108,
    // which Google takes as 1.91:1, and trimming it to 1199 would only lose a column.
    if (Math.abs(srcRatio - target.ratio) / target.ratio > 0.01) {
      if (srcRatio > target.ratio) sw = Math.round(sh * target.ratio);
      else sh = Math.round(sw / target.ratio);
    }
    const sx = Math.round((img.naturalWidth - sw) / 2);
    const sy = Math.round((img.naturalHeight - sh) / 2);
    // Never upscale past the original: a small image stays small and is said.
    const scale = Math.min(1, target.width / sw);
    const outW = Math.round(sw * scale);
    const outH = Math.round(sh * scale);
    const canvas = document.createElement("canvas");
    canvas.width = outW;
    canvas.height = outH;
    const ctx = canvas.getContext("2d");
    if (!ctx) throw new Error("This browser cannot prepare images.");
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, outW, outH);
    ctx.drawImage(img, sx, sy, sw, sh, 0, 0, outW, outH);
    const keepAlpha = shape === "logo" || shape === "landscape_logo";
    const blob = await new Promise<Blob | null>((resolve) =>
      canvas.toBlob(resolve, keepAlpha ? "image/png" : "image/jpeg", 0.9),
    );
    if (!blob) throw new Error("That image could not be prepared.");
    const buffer = new Uint8Array(await blob.arrayBuffer());
    let binary = "";
    for (let i = 0; i < buffer.length; i += 0x8000) {
      binary += String.fromCharCode(...buffer.subarray(i, i + 0x8000));
    }
    return { data: btoa(binary), small: outW < target.width };
  } finally {
    URL.revokeObjectURL(url);
  }
}

export function Images({
  draftId,
  shape,
  images,
  onChange,
  most,
  least,
  title,
}: {
  draftId: string;
  shape: Shape;
  images: AdImage[];
  onChange: (next: AdImage[]) => void;
  most: number;
  least?: number;
  title?: string;
}) {
  const input = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState("");
  const [trouble, setTrouble] = useState("");
  const spec = SHAPES[shape];

  async function add(files: FileList | null) {
    if (!files?.length) return;
    setTrouble("");
    const next = [...images];
    for (const file of Array.from(files)) {
      if (next.length >= most) break;
      setBusy(`Adding ${file.name}…`);
      try {
        const { data } = await cropped(file, shape);
        const { ok, data: back } = await call<AdImage>(`v2/${draftId}/images`, {
          shape,
          name: file.name.replace(/\.[a-z0-9]+$/i, "").slice(0, 80),
          data,
        });
        if (!ok) {
          setTrouble(said(back, "Google would not take that image."));
          continue;
        }
        next.push(back);
        onChange([...next]);
      } catch (error) {
        setTrouble(error instanceof Error ? error.message : "That image could not be added.");
      }
    }
    setBusy("");
    if (input.current) input.current.value = "";
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-pw-ink text-[14px] font-semibold">{title ?? spec.label}</p>
          <p className="text-pw-ink-500 text-[12px]">
            Recommended {spec.width} × {spec.height}, at least {spec.least}. JPG or PNG, up to 5 MB.
            {least ? ` At least ${least}, ` : " "}up to {most}.
          </p>
        </div>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => input.current?.click()}
          disabled={Boolean(busy) || images.length >= most}
          working={busy ? "Adding…" : false}
        >
          <ImageSquareIcon className="size-4" /> Add images
        </Button>
        <input
          ref={input}
          type="file"
          accept="image/png,image/jpeg,image/gif"
          multiple
          hidden
          onChange={(e) => add(e.target.files)}
        />
      </div>
      {busy ? (
        <p className="text-pw-ink-500 text-[13px]">
          {busy} It goes into your Google Ads asset library.
        </p>
      ) : null}
      {trouble ? <p className="text-pw-bad text-[13px]">{trouble}</p> : null}
      {images.length ? (
        <ul className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {images.map((img) => (
            <li
              key={img.asset}
              className="border-pw-border group relative overflow-hidden rounded-[12px] border"
            >
              <div
                className="bg-pw-muted flex items-center justify-center"
                style={{ aspectRatio: String(spec.ratio) }}
              >
                {img.url ? (
                  // Google's own hosted copy of the asset.
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={img.url} alt={img.name} className="size-full object-cover" />
                ) : (
                  <ImageSquareIcon className="text-pw-ink-300 size-8" />
                )}
              </div>
              <p className="text-pw-ink-500 truncate px-2 py-1 text-[11px]">
                {img.width} × {img.height}
              </p>
              <button
                type="button"
                aria-label={`Remove ${img.name}`}
                onClick={() => onChange(images.filter((i) => i.asset !== img.asset))}
                className="bg-pw-card/90 text-pw-ink hover:text-pw-bad absolute top-2 right-2 rounded-full p-1 opacity-0 shadow group-hover:opacity-100 focus:opacity-100"
              >
                <XIcon className="size-3" />
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

/** Money as the account writes it. */
export function money(amount: number | null | undefined, currency: string): string {
  if (amount === null || amount === undefined || Number.isNaN(amount)) return "—";
  try {
    return new Intl.NumberFormat(undefined, {
      style: "currency",
      currency: currency || "USD",
      maximumFractionDigits: amount < 10 ? 2 : 0,
    }).format(amount);
  } catch {
    return `${amount.toFixed(2)} ${currency}`;
  }
}
