"use client";

import { TrashIcon } from "@phosphor-icons/react";
import { Input } from "@/components/ui/field";
import { keywordText, parseKeyword, type Keyword, type Spec } from "@/lib/creation";
import { Labelled, NumberBox, Tick } from "../kit";
import { Act, LinesArea, count, useShared } from "./a-parts";

/*
  Google's "More settings" rows that are lists of small things: devices,
  campaign URL options, and negative keywords with shared lists.
*/

type Devices = Spec["devices"];
type Device = keyof Devices;

const DEVICE_LABEL: Record<Device, string> = {
  DESKTOP: "Computers",
  MOBILE: "Mobile phones",
  TABLET: "Tablets",
  CONNECTED_TV: "TV screens",
};

const SEARCH_DEVICES: Device[] = ["DESKTOP", "MOBILE", "TABLET"];
const PMAX_DEVICES: Device[] = ["DESKTOP", "MOBILE", "TABLET", "CONNECTED_TV"];

function without(devices: Devices, device: Device): Devices {
  const next = { ...devices };
  delete next[device];
  return next;
}

/** The Devices row's one-line summary. */
export function devicesSummary(devices: Devices, pmax: boolean): string {
  const list = pmax ? PMAX_DEVICES : SEARCH_DEVICES;
  const off = list.filter((d) => (devices[d] ?? 0) <= -100);
  const changed = pmax ? [] : list.filter((d) => devices[d] && (devices[d] ?? 0) > -100);
  if (!off.length && !changed.length) return "All devices";
  const out: string[] = [];
  if (off.length) out.push(`Not on ${off.map((d) => DEVICE_LABEL[d].toLowerCase()).join(" or ")}`);
  for (const d of changed) {
    const n = devices[d] ?? 0;
    out.push(`${DEVICE_LABEL[d]} ${n > 0 ? "+" : ""}${n}%`);
  }
  return out.join("; ");
}

/*
  Search: a bid adjustment per device, -100% to +900%, where -100% stops ads
  on it. Performance Max takes no adjustments, only which devices to show on.
  Either way at least one device has to stay on.
*/
export function DevicesEditor({
  devices,
  onChange,
  pmax,
  smart,
}: {
  devices: Devices;
  onChange: (next: Devices) => void;
  pmax: boolean;
  /** Smart Bidding uses only the -100% adjustments. */
  smart: boolean;
}) {
  const list = pmax ? PMAX_DEVICES : SEARCH_DEVICES;
  const on = (d: Device) => (devices[d] ?? 0) > -100;
  const onCount = list.filter(on).length;

  return (
    <div className="flex flex-col gap-4">
      <ul className="flex flex-col gap-4">
        {list.map((d) => (
          <li
            key={d}
            className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between"
          >
            <Tick
              checked={on(d)}
              disabled={on(d) && onCount === 1}
              onChange={(v) => onChange(v ? without(devices, d) : { ...devices, [d]: -100 })}
            >
              {pmax ? DEVICE_LABEL[d] : `Show ads on ${DEVICE_LABEL[d].toLowerCase()}`}
            </Tick>
            {!pmax && on(d) ? (
              <div className="sm:w-[200px]">
                <NumberBox
                  value={devices[d] ?? null}
                  // Zero is kept while typing; the server sends nothing for it.
                  onChange={(v) =>
                    onChange(v === null ? without(devices, d) : { ...devices, [d]: v })
                  }
                  unit="%"
                  min={-100}
                  max={900}
                  placeholder="0"
                  ariaLabel={`Bid adjustment for ${DEVICE_LABEL[d].toLowerCase()}`}
                />
              </div>
            ) : null}
          </li>
        ))}
      </ul>
      <p className="text-pw-ink-500 text-[13px] leading-[18px]">
        {pmax
          ? "Performance Max takes no bid adjustments. Untick a device to stop ads showing on it."
          : smart
            ? "Smart Bidding sets its own bids for each device, so it uses only a device turned off. Under Target CPA, an adjustment changes the target rather than the bid."
            : "A bid adjustment raises or lowers your bids on that device, from -100% to +900%. -100% stops ads on it."}
      </p>
    </div>
  );
}

type UrlOptions = Spec["url_options"];

export function urlSummary(o: UrlOptions): string {
  const out: string[] = [];
  if (o.tracking_template.trim()) out.push("Tracking template");
  if (o.final_url_suffix.trim()) out.push("Final URL suffix");
  const params = o.custom_parameters.filter((p) => p.key.trim()).length;
  if (params) out.push(count(params, "custom parameter"));
  return out.length ? out.join(", ") : "No options set";
}

/*
  Tracking template, final URL suffix and up to 8 custom parameters, as
  Google's "Campaign URL options" has them. A parameter's name is up to 16
  letters or numbers and is written {_name} in a template.
*/
export function UrlOptionsEditor({
  value,
  onChange,
  expanding,
}: {
  value: UrlOptions;
  onChange: (next: UrlOptions) => void;
  /** Final URL expansion is on: a template can break the pages Google picks. */
  expanding: boolean;
}) {
  const set = (patch: Partial<UrlOptions>) => onChange({ ...value, ...patch });
  const params = value.custom_parameters;
  const editParam = (at: number, patch: Partial<{ key: string; value: string }>) =>
    set({ custom_parameters: params.map((p, i) => (i === at ? { ...p, ...patch } : p)) });

  return (
    <div className="flex flex-col gap-4">
      <Labelled
        label="Tracking template"
        hint="Starts with {lpurl} or an https:// address. ValueTrack parameters are allowed."
      >
        <Input
          value={value.tracking_template}
          aria-label="Tracking template"
          placeholder="{lpurl}?source=google"
          spellCheck={false}
          onChange={(e) => set({ tracking_template: e.target.value })}
        />
      </Labelled>
      {expanding && value.tracking_template.trim() ? (
        <p className="text-pw-warn-ink text-[13px] leading-[18px]">
          With final URL expansion on, a tracking template can send people to a broken page. Google
          recommends a bare {"{lpurl}"} when no parameters are needed.
        </p>
      ) : null}
      <Labelled
        label="Final URL suffix"
        hint="Added to the end of your landing page address, such as utm_source=google."
      >
        <Input
          value={value.final_url_suffix}
          aria-label="Final URL suffix"
          placeholder="utm_source=google&utm_medium=cpc"
          spellCheck={false}
          onChange={(e) => set({ final_url_suffix: e.target.value })}
        />
      </Labelled>
      <div className="flex flex-col gap-2">
        <span className="text-pw-ink text-[13px] font-semibold">Custom parameters</span>
        {params.map((p, at) => (
          <div key={at} className="grid grid-cols-[1fr_auto] gap-2 sm:grid-cols-[200px_1fr_auto]">
            <Input
              value={p.key}
              aria-label={`Name of custom parameter ${at + 1}`}
              placeholder="Name"
              maxLength={16}
              spellCheck={false}
              onChange={(e) => editParam(at, { key: e.target.value.replace(/[^a-zA-Z0-9]/g, "") })}
              className="col-span-2 sm:col-span-1"
              trailing={
                <span className="text-pw-ink-400 text-[12px]">{`{_${p.key || "name"}}`}</span>
              }
            />
            <Input
              value={p.value}
              aria-label={`Value of custom parameter ${at + 1}`}
              placeholder="Value"
              maxLength={200}
              spellCheck={false}
              onChange={(e) => editParam(at, { value: e.target.value })}
            />
            <button
              type="button"
              aria-label={`Remove custom parameter ${at + 1}`}
              onClick={() => set({ custom_parameters: params.filter((_, i) => i !== at) })}
              className="text-pw-ink-400 hover:text-pw-bad hover:bg-pw-muted self-center rounded-full p-2"
            >
              <TrashIcon className="size-4" />
            </button>
          </div>
        ))}
        <div className="flex items-center justify-between gap-3">
          <Act
            onClick={() => set({ custom_parameters: [...params, { key: "", value: "" }] })}
            disabled={params.length >= 8}
          >
            + Add a custom parameter
          </Act>
          <span className="text-pw-ink-400 text-[12px]">{params.length} of 8</span>
        </div>
      </div>
    </div>
  );
}

export function negativesSummary(negatives: Keyword[], lists: number): string {
  if (!negatives.length && !lists) return "No negative keywords";
  const out: string[] = [];
  if (negatives.length) out.push(count(negatives.length, "negative keyword"));
  if (lists) out.push(count(lists, "shared list"));
  return out.join(", ");
}

/*
  Campaign negative keywords in Google's keyword box notation: a word for
  broad match, "quotes" for phrase, [brackets] for exact. A leading minus,
  as in Google's ad group keyword box, is dropped. Shared negative keyword
  lists are picked from the account's shared library (Search only: Google's
  API does not attach them to Performance Max).
*/
export function NegativesEditor({
  negatives,
  lists,
  onNegatives,
  onLists,
  shareable,
}: {
  negatives: Keyword[];
  lists: Spec["negative_lists"];
  onNegatives: (next: Keyword[]) => void;
  onLists: (next: Spec["negative_lists"]) => void;
  shareable: boolean;
}) {
  return (
    <div className="flex flex-col gap-4">
      <Labelled
        label="Negative keywords"
        hint={`One a line. word for broad match, "phrase" for phrase match, [exact] for exact match. ${negatives.length} of 10,000.`}
      >
        <LinesArea
          lines={negatives.map(keywordText)}
          ariaLabel="Negative keywords, one a line"
          placeholder={'free\n"diy guide"\n[jobs]'}
          rows={6}
          onChange={(lines) =>
            onNegatives(
              lines
                .map((line) => parseKeyword(line.replace(/^-\s*/, "")))
                .filter((k): k is Keyword => k !== null && k.text.length > 0),
            )
          }
        />
      </Labelled>
      {shareable ? <SharedLists value={lists} onChange={onLists} /> : null}
    </div>
  );
}

function SharedLists({
  value,
  onChange,
}: {
  value: Spec["negative_lists"];
  onChange: (next: Spec["negative_lists"]) => void;
}) {
  const { shared, trouble } = useShared();
  const picked = new Set(value.map((l) => l.resource));
  return (
    <div className="flex flex-col gap-2">
      <span className="text-pw-ink text-[13px] font-semibold">Negative keyword lists</span>
      {trouble ? (
        <p className="text-pw-bad text-[13px]">{trouble}</p>
      ) : !shared ? (
        <p className="text-pw-ink-500 text-[13px]">Looking in your shared library…</p>
      ) : !shared.negative_lists.length ? (
        <p className="text-pw-ink-500 text-[13px]">
          This account has no shared negative keyword lists.
        </p>
      ) : (
        shared.negative_lists.map((l) => (
          <Tick
            key={l.resource}
            checked={picked.has(l.resource)}
            onChange={(v) =>
              onChange(
                v
                  ? [...value, { resource: l.resource, name: l.name }]
                  : value.filter((x) => x.resource !== l.resource),
              )
            }
            help={count(l.count, "keyword")}
          >
            {l.name}
          </Tick>
        ))
      )}
    </div>
  );
}
