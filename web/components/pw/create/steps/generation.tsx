"use client";

import { MagicWandIcon, TimerIcon } from "@phosphor-icons/react";
import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { call, said, type Spec, type SpecDraft } from "@/lib/creation";
import type { StepProps } from "../editor";
import { Card, Chips, Note, Problems, Tick } from "../kit";
import { Area, Confirm, domainOf, isUrl, Pick, Section, Text } from "./b-form";

/*
  Google's "Keyword and asset generation": the landing page and a summary of
  the business go in, and ad groups with keywords, headlines and
  descriptions come out for the next step to review. PPCWay's version asks
  what the business sells, what kind of business it is and which promises
  are true, because its copy checks allow only claims the merchant ticked.
  Each product or service is one Keyword Planner call and one Otto call, run
  side by side, so it takes up to a minute. Nothing reaches Google here.
*/

type Generation = Spec["generation"];

/** "a, b and c", the way a sentence lists things. */
const listed = (items: string[]) =>
  items.length > 1
    ? `${items.slice(0, -1).join(", ")} and ${items[items.length - 1]}`
    : (items[0] ?? "");

export function StepGeneration({
  draft,
  spec,
  setup,
  change,
  problems,
  replace,
  go,
  flush,
}: StepProps) {
  const gen = spec.generation;
  // The campaign website fills the box until the merchant types in it; then the box is theirs.
  const [touched, setTouched] = useState(Boolean(gen.url));
  const url = touched ? gen.url : gen.url || spec.ways.website_url;
  const kinds = setup.kinds ?? [];
  const catalogue = setup.promises ?? [];
  const kind = kinds.find((k) => k.id === gen.kind);
  const set = (patch: Partial<Generation>) => change("generation", { ...gen, ...patch });

  const [working, setWorking] = useState(false);
  const [trouble, setTrouble] = useState("");
  const [asking, setAsking] = useState(false);
  const [more, setMore] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const started = useRef(0);

  useEffect(() => {
    if (!working) return;
    const timer = setInterval(
      () => setElapsed(Math.round((Date.now() - started.current) / 1000)),
      1000,
    );
    return () => clearInterval(timer);
  }, [working]);

  const usual = (kind?.promises ?? [])
    .map((id) => catalogue.find((p) => p.id === id))
    .filter((p): p is NonNullable<typeof p> => Boolean(p));
  const rest = catalogue.filter((p) => !usual.includes(p));
  // A promise ticked from the longer list stays in sight when the list is closed.
  const shownRest = more ? rest : rest.filter((p) => gen.promises.includes(p.id));
  const tick = (id: string, on: boolean) =>
    set({ promises: on ? [...gen.promises, id] : gen.promises.filter((p) => p !== id) });

  const blocked = !isUrl(url)
    ? "Add the page people land on, starting with https://."
    : !gen.services.length
      ? "Add at least one product or service you sell."
      : "";

  async function generate() {
    setAsking(false);
    setTrouble("");
    setElapsed(0);
    started.current = Date.now();
    setWorking(true);
    // Generation replaces the draft with the server's, so anything unsaved goes first.
    if (!(await flush())) {
      setWorking(false);
      setTrouble("Your latest changes could not be saved, so generation did not start. Try again.");
      return;
    }
    const { ok, data } = await call<SpecDraft>(`v2/${draft.id}/generate`, {
      url,
      summary: gen.summary,
      services: gen.services,
      kind: gen.kind,
      promises: gen.promises,
    });
    setWorking(false);
    if (!ok) {
      setTrouble(said(data, "Generation did not finish. Your answers are kept; try again."));
      return;
    }
    replace(data);
    go("ads");
  }

  const count = gen.services.length;
  const groups = spec.ad_groups.length;

  return (
    <div className="flex flex-col gap-5">
      <Problems items={problems} />
      {gen.done ? (
        <Note tone="good">
          Ad groups were generated from {domainOf(url) || "your page"} for{" "}
          {listed(gen.services) || "your products and services"}. Review and change them on the next
          step.{" "}
          <button type="button" onClick={() => go("ads")} className="font-semibold underline">
            Go to keywords and ads
          </button>
        </Note>
      ) : null}

      <Card
        title="Keyword and asset generation"
        help="Tell PPCWay about your business and it writes your ad groups: keywords from real searches, and headlines and descriptions for each product or service."
      >
        <Section title="Landing page" help="The page people reach when they click your ads.">
          <Text
            label="Landing page URL"
            type="url"
            value={url}
            placeholder="https://www.example.com"
            onChange={(v) => {
              setTouched(true);
              set({ url: v });
            }}
          />
        </Section>

        <Section
          title="Business summary"
          help="In a few sentences, what you do and who for. Google's AI writes one from your page for you to edit; here you write it, and Otto reads it before writing your ads. It describes; only the promises you tick below can appear as claims."
        >
          <Area
            label="Business summary"
            value={gen.summary}
            most={2000}
            rows={4}
            placeholder="What you do, for whom and where, in a few sentences. For example: we sell handmade soy candles online and ship across Canada."
            onChange={(summary) => set({ summary })}
          />
        </Section>

        <Section
          title="What do you sell?"
          help="Each product or service becomes its own ad group, with its own keywords and ad. Up to 10."
        >
          <Chips
            values={gen.services}
            onChange={(services) => set({ services })}
            most={10}
            longest={80}
            placeholder={
              kind?.services_hint || "A product or service, as a customer would search for it"
            }
            ariaLabel="Add a product or service"
          />
        </Section>

        <Section
          title="Your business"
          help="So the ads are written for your kind of business, and only make promises you can keep."
        >
          {kinds.length ? (
            <Pick
              label="Kind of business"
              value={gen.kind}
              options={[
                { value: "", label: "Choose one" },
                ...kinds.map((k) => ({ value: k.id, label: k.label })),
              ]}
              onChange={(v) => set({ kind: v })}
              hint={kind ? `For example: ${kind.examples}.` : undefined}
              className="max-w-[420px]"
            />
          ) : null}
          {catalogue.length ? (
            <fieldset className="flex flex-col gap-3">
              <legend className="text-pw-ink mb-1 text-[13px] font-semibold">
                What can you truly promise?
              </legend>
              <p className="text-pw-ink-500 -mt-1 text-[12px] leading-[17px]">
                Tick only what is true for every customer. Otto writes only the promises you tick,
                and PPCWay&apos;s checks flag any ad line that makes one you have not.
              </p>
              <div className="grid gap-2 sm:grid-cols-2">
                {[...usual, ...shownRest].map((p) => (
                  <Tick
                    key={p.id}
                    checked={gen.promises.includes(p.id)}
                    onChange={(on) => tick(p.id, on)}
                  >
                    {p.label}
                  </Tick>
                ))}
              </div>
              {!more && rest.length > shownRest.length ? (
                <button
                  type="button"
                  onClick={() => setMore(true)}
                  className="text-pw-blue self-start text-[13px] font-semibold"
                >
                  Show {rest.length - shownRest.length} more{" "}
                  {rest.length - shownRest.length === 1 ? "promise" : "promises"}
                </button>
              ) : null}
            </fieldset>
          ) : null}
        </Section>

        <Section title="Generate">
          <Note>
            Keywords come only from searches Google&apos;s Keyword Planner says people make where
            your ads will show; an idea it cannot confirm is left out and you see why. Otto then
            writes 15 headlines and 4 descriptions for each product or service, and every line
            passes PPCWay&apos;s checks before you see it. Nothing goes to Google until you publish.
          </Note>

          {asking ? (
            <Confirm
              words={`Generating again replaces the ${groups} ad ${groups === 1 ? "group" : "groups"} on the next step, with every keyword and ad in them, including your changes.`}
              yes="Replace them"
              onYes={generate}
              onNo={() => setAsking(false)}
            />
          ) : null}

          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <Button
              onClick={() => (gen.done && groups ? setAsking(true) : void generate())}
              disabled={Boolean(blocked) || asking}
              working={working ? "Generating…" : false}
            >
              <MagicWandIcon className="size-4" /> {gen.done ? "Generate again" : "Generate"}
            </Button>
            <button
              type="button"
              onClick={() => go("ads")}
              disabled={working}
              className="text-pw-blue disabled:text-pw-ink-300 self-start text-[14px] font-semibold sm:self-center"
            >
              Skip and write your own
            </button>
          </div>
          {blocked && !working ? <p className="text-pw-ink-500 text-[13px]">{blocked}</p> : null}

          {working ? (
            <div
              className="bg-pw-muted text-pw-ink-700 flex items-start gap-3 rounded-[12px] px-4 py-3 text-[13px] leading-[19px]"
              aria-live="polite"
            >
              <TimerIcon className="text-pw-blue mt-[1px] size-4 shrink-0" />
              <p>
                {elapsed < 60
                  ? `Reading ${domainOf(url) || "your page"}, then asking Keyword Planner which searches people make and having Otto write ads, for ${count} ${count === 1 ? "product or service" : "products and services"} side by side. It usually takes under a minute.`
                  : "Still working. Keyword Planner can be slow; this page moves on by itself when the ad groups are ready."}{" "}
                <span className="text-pw-ink-500 tabular-nums">
                  {elapsed} {elapsed === 1 ? "second" : "seconds"} so far.
                </span>
              </p>
            </div>
          ) : null}
          {trouble ? <Note tone="bad">{trouble}</Note> : null}
        </Section>
      </Card>
    </div>
  );
}
