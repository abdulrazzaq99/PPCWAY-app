"use client";

import { PlusIcon, TrashIcon } from "@phosphor-icons/react";
import { useState, type ReactNode } from "react";
import { Input } from "@/components/ui/field";
import { LIMITS, type AdImage, type Snippet, type Spec } from "@/lib/creation";
import { Card, Images, Lines, Note, Panel, Toggle } from "../kit";
import {
  AppForm,
  LeadFormForm,
  newLeadForm,
  newPrice,
  newPromotion,
  PriceForm,
  PromotionForm,
} from "./b-asset-forms";
import { Pick, Quiet, Text } from "./b-form";
import { OCCASIONS, PRICE_TYPES, SNIPPET_HEADERS, STORES } from "./b-options";
import { Sitelinks } from "./b-sitelinks";

/*
  The campaign's assets, the extra lines and pictures Google can show with
  the ad. Google's step shows Sitelinks, Callouts and Calls straight away and
  keeps the rest behind "+ Ad asset"; so does this. An asset type with
  something in it is always shown, whichever way it was added.
*/

type Assets = Spec["assets"];
type Extra =
  | "snippets"
  | "images"
  | "business_name"
  | "logo"
  | "price"
  | "promotion"
  | "lead_form"
  | "app"
  | "location";

const EXTRAS: { id: Extra; label: string; help: string }[] = [
  {
    id: "snippets",
    label: "Structured snippets",
    help: "A header and a list, such as Types: a, b, c",
  },
  { id: "images", label: "Images", help: "Pictures beside the ad" },
  { id: "business_name", label: "Business name", help: "Your name, shown with the ad" },
  { id: "logo", label: "Business logo", help: "Your logo, shown with the ad" },
  { id: "price", label: "Price", help: "3 to 8 things you sell, with prices" },
  { id: "promotion", label: "Promotion", help: "A sale or offer" },
  { id: "lead_form", label: "Lead form", help: "A form inside the ad" },
  { id: "app", label: "App", help: "A link to your app" },
  { id: "location", label: "Location", help: "Your address, from Google Business Profile" },
];

function filled(a: Assets, id: Extra): boolean {
  switch (id) {
    case "snippets":
      return a.snippets.length > 0;
    case "images":
      return a.images.length > 0;
    case "business_name":
      return Boolean(a.business_name);
    case "logo":
      return a.logo !== null;
    case "price":
      return a.price !== null;
    case "promotion":
      return a.promotion !== null;
    case "lead_form":
      return a.lead_form !== null;
    case "app":
      return a.app !== null;
    default:
      return false;
  }
}

const label = (list: readonly { value: string; label: string }[], value: string) =>
  list.find((o) => o.value === value)?.label ?? value;

const square = (i: AdImage) => i.width > 0 && i.width === i.height;

export function AssetsCard({
  spec,
  change,
  draftId,
}: {
  spec: Spec;
  change: (next: Assets) => void;
  draftId: string;
}) {
  const a = spec.assets;
  const ways = spec.ways;
  const landing = ways.website_url || spec.generation.url;
  const set = (patch: Partial<Assets>) => change({ ...a, ...patch });
  // What the merchant said on step 1 opens the matching asset without asking.
  const [added, setAdded] = useState<Set<Extra>>(
    () =>
      new Set<Extra>([
        ...(ways.lead_forms ? (["lead_form"] as Extra[]) : []),
        ...(ways.app ? (["app"] as Extra[]) : []),
      ]),
  );
  const [menu, setMenu] = useState(false);
  const [fresh, setFresh] = useState<Extra | null>(null);
  const shown = (id: Extra) => added.has(id) || filled(a, id);
  const hide = (id: Extra, patch: Partial<Assets>) => {
    setAdded((s) => {
      const next = new Set(s);
      next.delete(id);
      return next;
    });
    if (Object.keys(patch).length) set(patch);
  };
  const add = (id: Extra) => {
    setMenu(false);
    setFresh(id);
    setAdded((s) => new Set(s).add(id));
    if (id === "price" && !a.price) set({ price: newPrice() });
    if (id === "promotion" && !a.promotion) set({ promotion: newPromotion() });
    if (id === "lead_form" && !a.lead_form)
      set({ lead_form: newLeadForm(a.business_name || spec.name) });
    if (id === "app" && !a.app)
      set({ app: { app_id: ways.app_id, store: ways.app_store, link_text: "" } });
    if (id === "snippets" && !a.snippets.length)
      set({ snippets: [{ header: "Types", values: ["", "", ""] }] });
  };
  const remove = (id: Extra, patch: Partial<Assets>, what: string) => (
    <Quiet tone="red" onClick={() => hide(id, patch)}>
      <TrashIcon className="size-4" /> Remove {what}
    </Quiet>
  );

  const squares = a.images.filter(square);
  const wides = a.images.filter((i) => !square(i));
  const callNumber = a.call_number || ways.phone_number;
  const callCountry = a.call_country || ways.phone_country;
  const liveLinks = a.sitelinks.filter((s) => s.text.trim()).length;
  const liveCallouts = a.callouts.filter((c) => c.trim());

  const lazy = (id: Extra, panel: ReactNode) => (shown(id) ? panel : null);
  const leftover = EXTRAS.filter((e) => !shown(e.id));

  return (
    <Card
      title="Assets"
      help="Extra lines and pictures Google can show with your ads, for every ad group in this campaign. More assets usually mean bigger ads and more clicks."
    >
      <Panel
        title="Sitelinks"
        summary={
          liveLinks
            ? `${liveLinks} ${liveLinks === 1 ? "sitelink" : "sitelinks"}`
            : "None yet. Google recommends at least 4."
        }
      >
        <Sitelinks
          links={a.sitelinks}
          onChange={(sitelinks) => set({ sitelinks })}
          landing={landing}
        />
      </Panel>

      <Panel
        title="Callouts"
        summary={
          liveCallouts.length
            ? liveCallouts.slice(0, 4).join(" · ")
            : "None yet. Short points such as Free delivery."
        }
      >
        <p className="text-pw-ink-500 text-[13px] leading-[18px]">
          Up to 25 characters each. Google shows up to 10 with an ad, under the description.
        </p>
        <Lines
          values={a.callouts}
          onChange={(callouts) => set({ callouts })}
          most={20}
          longest={LIMITS.callout}
          placeholder="Callout"
          addLabel="Callout"
        />
      </Panel>

      <Panel
        title="Calls"
        summary={
          a.call
            ? `${callNumber || "No number yet"}${callCountry ? ` (${callCountry})` : ""}`
            : "Off"
        }
      >
        <Toggle
          on={a.call}
          onChange={(on) =>
            set({
              call: on,
              call_number: on && !a.call_number ? ways.phone_number : a.call_number,
              call_country: on && !a.call_country ? ways.phone_country : a.call_country,
            })
          }
          help="A call button on phones and your number on computers. Google checks the number belongs to your business; no premium or fax numbers."
        >
          Add a phone number to your ads
        </Toggle>
        {a.call ? (
          <div className="grid gap-3 sm:grid-cols-[120px_1fr]">
            <label className="flex flex-col gap-[6px]">
              <span className="text-pw-ink text-[13px] font-semibold">Country</span>
              <Input
                value={callCountry}
                maxLength={2}
                placeholder="US"
                onChange={(e) => set({ call_country: e.target.value.toUpperCase() })}
              />
            </label>
            <Text
              label="Phone number"
              type="tel"
              value={callNumber}
              placeholder="+1 416 555 0100"
              onChange={(call_number) => set({ call_number })}
            />
          </div>
        ) : null}
      </Panel>

      {lazy(
        "snippets",
        <Panel
          title="Structured snippets"
          open={fresh === "snippets"}
          summary={
            a.snippets
              .map((s) => `${s.header}: ${s.values.filter((v) => v.trim()).length} values`)
              .join(", ") || "None"
          }
        >
          <SnippetList snippets={a.snippets} onChange={(snippets) => set({ snippets })} />
          {remove("snippets", { snippets: [] }, "structured snippets")}
        </Panel>,
      )}

      {lazy(
        "images",
        <Panel
          title="Images"
          open={fresh === "images"}
          summary={
            a.images.length ? `${squares.length} square, ${wides.length} landscape` : "None yet"
          }
        >
          <Note>
            Google shows image assets only on accounts open 60 days or more, with a good policy
            history and Search spend in the last 30 days. At least one square image is required;
            landscape ones are optional. Up to 20 in all; keep the subject in the middle 80%.
          </Note>
          <Images
            draftId={draftId}
            shape="square"
            title="Square (1:1)"
            images={squares}
            most={20 - wides.length}
            least={1}
            onChange={(next) => set({ images: [...next, ...wides] })}
          />
          <Images
            draftId={draftId}
            shape="landscape"
            title="Landscape (1.91:1)"
            images={wides}
            most={20 - squares.length}
            onChange={(next) => set({ images: [...squares, ...next] })}
          />
          {remove("images", { images: [] }, "all images")}
        </Panel>,
      )}

      {lazy(
        "business_name",
        <Panel
          title="Business name"
          open={fresh === "business_name"}
          summary={a.business_name || "Not set"}
        >
          <Text
            label="Business name"
            value={a.business_name}
            most={LIMITS.businessName}
            hint="It must match your website's domain or your verified legal name. Google shows it once the account has Search spend in the last 28 days."
            onChange={(business_name) => set({ business_name })}
          />
          {remove("business_name", { business_name: "" }, "business name")}
        </Panel>,
      )}

      {lazy(
        "logo",
        <Panel
          title="Business logo"
          open={fresh === "logo"}
          summary={a.logo ? "Added" : "Not added"}
        >
          <Images
            draftId={draftId}
            shape="logo"
            title="Square logo (1:1)"
            images={a.logo ? [a.logo] : []}
            most={1}
            onChange={(next) => set({ logo: next[0] ?? null })}
          />
          <p className="text-pw-ink-500 text-[12px]">
            One logo per campaign. Like the business name, it must match your domain or verified
            name.
          </p>
          {remove("logo", { logo: null }, "logo")}
        </Panel>,
      )}

      {lazy(
        "price",
        <Panel
          title="Price"
          open={fresh === "price"}
          summary={
            a.price
              ? `${label(PRICE_TYPES, a.price.type)}, ${a.price.items.filter((i) => i.header.trim()).length} items`
              : "None"
          }
        >
          {a.price ? (
            <PriceForm
              price={a.price}
              onChange={(price) => set({ price })}
              currency={spec.currency}
              landing={landing}
            />
          ) : null}
          {remove("price", { price: null }, "price asset")}
        </Panel>,
      )}

      {lazy(
        "promotion",
        <Panel
          title="Promotion"
          open={fresh === "promotion"}
          summary={
            a.promotion?.item
              ? `${a.promotion.amount || ""}${a.promotion.discount === "percent" ? "%" : ` ${spec.currency}`} off ${a.promotion.item}${a.promotion.occasion ? `, ${label(OCCASIONS, a.promotion.occasion)}` : ""}`
              : "Not filled in yet"
          }
        >
          {a.promotion ? (
            <PromotionForm
              promotion={a.promotion}
              onChange={(promotion) => set({ promotion })}
              currency={spec.currency}
              landing={landing}
            />
          ) : null}
          {remove("promotion", { promotion: null }, "promotion")}
        </Panel>,
      )}

      {lazy(
        "lead_form",
        <Panel
          title="Lead form"
          open={fresh === "lead_form"}
          summary={a.lead_form?.headline || "Not filled in yet"}
        >
          {a.lead_form ? (
            <LeadFormForm
              form={a.lead_form}
              onChange={(lead_form) => set({ lead_form })}
              businessName={a.business_name || spec.name}
            />
          ) : (
            <Quiet onClick={() => set({ lead_form: newLeadForm(a.business_name || spec.name) })}>
              + Start a lead form
            </Quiet>
          )}
          {remove("lead_form", { lead_form: null }, "lead form")}
        </Panel>,
      )}

      {lazy(
        "app",
        <Panel
          title="App"
          open={fresh === "app"}
          summary={
            a.app?.app_id ? `${a.app.app_id}, ${label(STORES, a.app.store)}` : "Not filled in yet"
          }
        >
          {a.app ? (
            <AppForm app={a.app} onChange={(app) => set({ app })} />
          ) : (
            <Quiet
              onClick={() =>
                set({ app: { app_id: ways.app_id, store: ways.app_store, link_text: "" } })
              }
            >
              + Add your app
            </Quiet>
          )}
          {remove("app", { app: null }, "app")}
        </Panel>,
      )}

      {lazy(
        "location",
        <Panel
          title="Location"
          open={fresh === "location"}
          summary="From a Google Business Profile"
        >
          <Note>
            Google takes location assets from a Google Business Profile linked to the ads account,
            in Google Ads under Tools, Shared library, Location manager. PPCWay cannot link a
            profile yet; once you link one there, Google can show your address with these ads.
          </Note>
          <Quiet tone="red" onClick={() => hide("location", {})}>
            <TrashIcon className="size-4" /> Hide
          </Quiet>
        </Panel>,
      )}

      <div className="relative px-6 py-4">
        <button
          type="button"
          aria-expanded={menu}
          onClick={() => setMenu((m) => !m)}
          disabled={!leftover.length}
          className="text-pw-blue disabled:text-pw-ink-300 inline-flex items-center gap-1 text-[14px] font-semibold"
        >
          <PlusIcon className="size-4" /> Ad asset
        </button>
        {menu ? (
          <ul className="border-pw-border bg-pw-card divide-pw-border mt-2 max-w-[420px] divide-y rounded-[12px] border shadow-sm">
            {leftover.map((e) => (
              <li key={e.id}>
                <button
                  type="button"
                  onClick={() => add(e.id)}
                  className="hover:bg-pw-muted flex w-full flex-col px-4 py-[10px] text-left"
                >
                  <span className="text-pw-ink text-[14px] font-semibold">{e.label}</span>
                  <span className="text-pw-ink-500 text-[12px]">{e.help}</span>
                </button>
              </li>
            ))}
          </ul>
        ) : null}
      </div>
    </Card>
  );
}

/** Structured snippets: Google's fixed headers, 3 to 10 values of up to 25 characters. */
function SnippetList({
  snippets,
  onChange,
}: {
  snippets: Snippet[];
  onChange: (next: Snippet[]) => void;
}) {
  const set = (at: number, patch: Partial<Snippet>) =>
    onChange(snippets.map((s, i) => (i === at ? { ...s, ...patch } : s)));
  const headers = SNIPPET_HEADERS.map((h) => ({ value: h as string, label: h as string }));
  return (
    <div className="flex flex-col gap-3">
      <p className="text-pw-ink-500 text-[13px] leading-[18px]">
        Google shows up to 2 headers on a computer and 1 on a phone. Each value must fit the header:
        under Types, the kinds of thing you offer.
      </p>
      {snippets.map((s, at) => (
        <fieldset
          key={at}
          className="border-pw-border flex flex-col gap-3 rounded-[14px] border p-4"
        >
          <legend className="text-pw-ink-500 px-1 text-[12px] font-semibold">
            Snippet {at + 1}
          </legend>
          <Pick
            label="Header"
            value={s.header}
            options={headers}
            onChange={(header) => set(at, { header })}
            className="max-w-[320px]"
          />
          <Lines
            values={s.values}
            onChange={(values) => set(at, { values })}
            most={10}
            least={3}
            longest={LIMITS.snippetValue}
            placeholder="Value"
            addLabel="Value"
          />
          <Quiet tone="red" onClick={() => onChange(snippets.filter((_, i) => i !== at))}>
            <TrashIcon className="size-4" /> Remove snippet {at + 1}
          </Quiet>
        </fieldset>
      ))}
      <Quiet onClick={() => onChange([...snippets, { header: "Types", values: ["", "", ""] }])}>
        + Structured snippet
      </Quiet>
    </div>
  );
}
