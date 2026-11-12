"use client";

import { TrashIcon } from "@phosphor-icons/react";
import type { AppLink, LeadForm, Price, PriceItem, Promotion } from "@/lib/creation";
import { Note, NumberBox, Tick } from "../kit";
import { Area, Pick, Quiet, Text } from "./b-form";
import {
  LEAD_CTAS,
  LEAD_FIELDS,
  OCCASIONS,
  PRICE_QUALIFIERS,
  PRICE_TYPES,
  PRICE_UNITS,
  PROMOTION_DETAILS,
  PROMOTION_TYPES,
  STORES,
} from "./b-options";

/*
  The forms for Google's less common assets, field for field as its asset
  forms have them, with the limits the server cuts to (`builder/ops.py`).
*/

function Amount({
  label,
  value,
  onChange,
  unit,
}: {
  label: string;
  value: number;
  onChange: (next: number) => void;
  unit: string;
}) {
  return (
    <div className="flex min-w-0 flex-col gap-[6px]">
      <span className="text-pw-ink text-[13px] leading-[18px] font-semibold">{label}</span>
      <NumberBox
        value={value || null}
        onChange={(v) => onChange(v ?? 0)}
        unit={unit}
        min={0}
        step={0.01}
        ariaLabel={label}
      />
    </div>
  );
}

const NEW_ITEM: PriceItem = { header: "", description: "", price: 0, unit: "", final_url: "" };

export function newPrice(): Price {
  return {
    type: "SERVICES",
    qualifier: "",
    language: "en",
    items: [0, 1, 2].map(() => ({ ...NEW_ITEM })),
  };
}

/** Price asset: a type, an optional qualifier, and 3 to 8 items. */
export function PriceForm({
  price,
  onChange,
  currency,
  landing,
}: {
  price: Price;
  onChange: (next: Price) => void;
  currency: string;
  landing: string;
}) {
  const set = (patch: Partial<Price>) => onChange({ ...price, ...patch });
  const setItem = (at: number, patch: Partial<PriceItem>) =>
    set({ items: price.items.map((item, i) => (i === at ? { ...item, ...patch } : item)) });
  const live = price.items.filter((i) => i.header.trim()).length;
  return (
    <div className="flex flex-col gap-4">
      <div className="grid gap-3 sm:grid-cols-2">
        <Pick
          label="Type"
          value={price.type}
          options={PRICE_TYPES}
          onChange={(type) => set({ type })}
        />
        <Pick
          label="Price qualifier"
          value={price.qualifier}
          options={PRICE_QUALIFIERS}
          onChange={(qualifier) => set({ qualifier })}
        />
      </div>
      {price.items.map((item, at) => (
        <fieldset
          key={at}
          className="border-pw-border flex flex-col gap-3 rounded-[14px] border p-4"
        >
          <legend className="text-pw-ink-500 px-1 text-[12px] font-semibold">Item {at + 1}</legend>
          <div className="grid gap-3 sm:grid-cols-2">
            <Text
              label="Header"
              value={item.header}
              most={25}
              onChange={(header) => setItem(at, { header })}
            />
            <Text
              label="Description"
              value={item.description}
              most={25}
              onChange={(description) => setItem(at, { description })}
            />
            <Amount
              label="Price"
              value={item.price}
              unit={currency}
              onChange={(p) => setItem(at, { price: p })}
            />
            <Pick
              label="Unit"
              value={item.unit}
              options={PRICE_UNITS}
              onChange={(unit) => setItem(at, { unit })}
            />
            <Text
              label="Final URL"
              type="url"
              value={item.final_url}
              placeholder={landing || "https://"}
              hint={item.final_url ? undefined : "Empty opens your campaign website."}
              onChange={(final_url) => setItem(at, { final_url })}
              className="sm:col-span-2"
            />
          </div>
          <Quiet tone="red" onClick={() => set({ items: price.items.filter((_, i) => i !== at) })}>
            <TrashIcon className="size-4" /> Remove item {at + 1}
          </Quiet>
        </fieldset>
      ))}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Quiet
          onClick={() => set({ items: [...price.items, { ...NEW_ITEM }] })}
          disabled={price.items.length >= 8}
        >
          + Item
        </Quiet>
        <span className="text-pw-ink-400 text-[12px]">{live} of 8, at least 3</span>
      </div>
    </div>
  );
}

export function newPromotion(): Promotion {
  return {
    item: "",
    occasion: "",
    discount: "percent",
    amount: 0,
    up_to: false,
    details: "none",
    code: "",
    orders_over: 0,
    final_url: "",
    start: null,
    end: null,
    language: "en",
  };
}

/** Promotion asset: what is off, on what, and when. */
export function PromotionForm({
  promotion: p,
  onChange,
  currency,
  landing,
}: {
  promotion: Promotion;
  onChange: (next: Promotion) => void;
  currency: string;
  landing: string;
}) {
  const set = (patch: Partial<Promotion>) => onChange({ ...p, ...patch });
  const kind = `${p.up_to ? "up_to_" : ""}${p.discount}`;
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <Pick
        label="Occasion"
        value={p.occasion}
        options={OCCASIONS}
        onChange={(occasion) => set({ occasion })}
      />
      <Pick
        label="Promotion type"
        value={kind}
        options={PROMOTION_TYPES}
        onChange={(v) =>
          set({
            up_to: v.startsWith("up_to_"),
            discount: v.endsWith("percent") ? "percent" : "money",
          })
        }
      />
      <Amount
        label={p.discount === "percent" ? "Percent off" : "Amount off"}
        value={p.amount}
        unit={p.discount === "percent" ? "%" : currency}
        onChange={(amount) => set({ amount })}
      />
      <Text
        label="Item"
        value={p.item}
        most={20}
        placeholder="Spring tune-ups"
        hint="What the promotion is on."
        onChange={(item) => set({ item })}
      />
      <Text
        label="Final URL"
        type="url"
        value={p.final_url}
        placeholder={landing || "https://"}
        hint={p.final_url ? undefined : "Empty opens your campaign website."}
        onChange={(final_url) => set({ final_url })}
        className="sm:col-span-2"
      />
      <Pick
        label="Promotion details"
        value={p.details}
        options={PROMOTION_DETAILS}
        onChange={(details) => set({ details })}
      />
      {p.details === "code" ? (
        <Text label="Promo code" value={p.code} most={15} onChange={(code) => set({ code })} />
      ) : p.details === "orders_over" ? (
        <Amount
          label="Orders over"
          value={p.orders_over}
          unit={currency}
          onChange={(orders_over) => set({ orders_over })}
        />
      ) : (
        <span className="hidden sm:block" />
      )}
      <Text
        label="Start date (optional)"
        type="date"
        value={p.start ?? ""}
        onChange={(v) => set({ start: v || null })}
      />
      <Text
        label="End date (optional)"
        type="date"
        value={p.end ?? ""}
        onChange={(v) => set({ end: v || null })}
      />
    </div>
  );
}

export function newLeadForm(businessName: string): LeadForm {
  return {
    business_name: businessName.slice(0, 25),
    headline: "",
    description: "",
    privacy_policy_url: "",
    call_to_action: "LEARN_MORE",
    call_to_action_description: "",
    fields: ["FULL_NAME", "EMAIL", "PHONE_NUMBER"],
    post_submit_headline: "",
    post_submit_description: "",
  };
}

/** Lead form asset: the form Google shows inside the ad, and what it says after. */
export function LeadFormForm({
  form,
  onChange,
  businessName,
}: {
  form: LeadForm;
  onChange: (next: LeadForm) => void;
  businessName: string;
}) {
  const set = (patch: Partial<LeadForm>) => onChange({ ...form, ...patch });
  return (
    <div className="flex flex-col gap-4">
      <Note>
        Google offers lead forms to accounts with a good policy history in eligible industries, on a
        bid strategy that aims for conversions, with a lead form conversion goal. Some accounts must
        complete advertiser verification first. Leads can be downloaded from Google Ads for 30 days.
      </Note>
      <div className="grid gap-3 sm:grid-cols-2">
        <Text
          label="Headline"
          value={form.headline}
          most={30}
          onChange={(headline) => set({ headline })}
        />
        <Text
          label="Business name"
          value={form.business_name}
          most={25}
          placeholder={businessName}
          onChange={(business_name) => set({ business_name })}
        />
      </div>
      <Area
        label="Description"
        value={form.description}
        most={200}
        rows={3}
        hint="What people get for filling it in."
        onChange={(description) => set({ description })}
      />
      <fieldset className="flex flex-col gap-2">
        <legend className="text-pw-ink mb-2 text-[13px] font-semibold">Questions</legend>
        <div className="grid gap-2 sm:grid-cols-2">
          {LEAD_FIELDS.map((f) => (
            <Tick
              key={f.value}
              checked={form.fields.includes(f.value)}
              onChange={(on) =>
                set({
                  fields: on ? [...form.fields, f.value] : form.fields.filter((x) => x !== f.value),
                })
              }
            >
              {f.label}
            </Tick>
          ))}
        </div>
      </fieldset>
      <Text
        label="Privacy policy URL"
        type="url"
        value={form.privacy_policy_url}
        placeholder="https://"
        hint="Google requires a link to your privacy policy on the form."
        onChange={(privacy_policy_url) => set({ privacy_policy_url })}
      />
      <div className="grid gap-3 sm:grid-cols-2">
        <Pick
          label="Call to action"
          value={form.call_to_action}
          options={LEAD_CTAS}
          onChange={(call_to_action) => set({ call_to_action })}
        />
        <Text
          label="Call to action description"
          value={form.call_to_action_description}
          most={30}
          placeholder="Get a quote today"
          onChange={(call_to_action_description) => set({ call_to_action_description })}
        />
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <Text
          label="Headline after submitting (optional)"
          value={form.post_submit_headline}
          most={30}
          placeholder="Thanks, we'll be in touch"
          onChange={(post_submit_headline) => set({ post_submit_headline })}
        />
      </div>
      <Area
        label="Description after submitting (optional)"
        value={form.post_submit_description}
        most={200}
        rows={2}
        onChange={(post_submit_description) => set({ post_submit_description })}
      />
    </div>
  );
}

/** App asset: a link to the app under the ad. */
export function AppForm({ app, onChange }: { app: AppLink; onChange: (next: AppLink) => void }) {
  const set = (patch: Partial<AppLink>) => onChange({ ...app, ...patch });
  return (
    <div className="grid gap-3 sm:grid-cols-3">
      <Pick
        label="App store"
        value={app.store}
        options={STORES}
        onChange={(store) => set({ store })}
      />
      <Text
        label="App id"
        value={app.app_id}
        placeholder={app.store === "APPLE_APP_STORE" ? "123456789" : "com.example.app"}
        onChange={(app_id) => set({ app_id: app_id.trim() })}
      />
      <Text
        label="Link text"
        value={app.link_text}
        most={25}
        placeholder="Get the app"
        onChange={(link_text) => set({ link_text })}
      />
    </div>
  );
}
