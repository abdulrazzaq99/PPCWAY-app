"use client";

import { PlusIcon } from "@phosphor-icons/react";
import { Button } from "@/components/ui/button";
import type { AdImage, DemandGenAd, Spec } from "@/lib/creation";
import type { StepProps } from "../editor";
import { Card, Images, Labelled, Lines, Note, Problems } from "../kit";
import { Section, Text } from "./b-form";
import { Videos } from "./b-pmax";
import { CtaText, DemandGenAdEditor, newDemandGenAd } from "./c-ads";
import { DisplayPreview } from "./c-preview";

/*
  The ads step for Demand Gen, Display and App. Demand Gen: a list of ads,
  each an image, video or carousel ad, as Google's step 6 has them. Display:
  one responsive display ad, which Google fits to every ad space. App: the
  text, images and videos Google mixes with what it reads from the store
  listing. Every change is the whole section, saved a moment later.
*/

export function StepMoreAds(props: StepProps) {
  if (props.spec.type === "DEMAND_GEN") return <DemandGenAds {...props} />;
  if (props.spec.type === "DISPLAY") return <DisplayAd {...props} />;
  if (props.spec.type === "APP") return <AppAds {...props} />;
  return null;
}

function landingOf(spec: Spec): string {
  return spec.ways.website_url || spec.generation.url;
}

function DemandGenAds({ draft, spec, change, problems }: StepProps) {
  const dg = spec.demand_gen;
  const setAds = (ads: DemandGenAd[]) => change("demand_gen", { ...dg, ads });
  const formats = dg.ads.map((a) => a.format);
  const tally = (["image", "video", "carousel"] as const)
    .map((f) => {
      const n = formats.filter((x) => x === f).length;
      return n ? `${n} ${f} ${n === 1 ? "ad" : "ads"}` : "";
    })
    .filter(Boolean)
    .join(", ");

  return (
    <div className="flex flex-col gap-5">
      <Problems items={problems} />
      <p className="text-pw-ink-700 text-[14px] leading-[20px]">
        {dg.ads.length
          ? `This ad group has ${dg.ads.length} ${dg.ads.length === 1 ? "ad" : "ads"}: ${tally}. Google recommends both an image ad and a video ad, so your ads can show on every channel.`
          : "This ad group has no ads yet. Add at least one."}
      </p>
      {dg.ads.map((ad, at) => (
        <DemandGenAdEditor
          // Ads have no ids before publishing; their place in the list is who they are.
          key={at}
          ad={ad}
          at={at}
          draftId={draft.id}
          landing={landingOf(spec)}
          businessFallback={spec.assets.business_name}
          onChange={(next) => setAds(dg.ads.map((a, i) => (i === at ? next : a)))}
          onRemove={dg.ads.length > 1 ? () => setAds(dg.ads.filter((_, i) => i !== at)) : undefined}
        />
      ))}
      <div>
        <Button variant="secondary" onClick={() => setAds([...dg.ads, newDemandGenAd(dg.ads)])}>
          <PlusIcon className="size-4" /> Add another ad
        </Button>
      </div>
    </div>
  );
}

/** Google caps a responsive display ad at 15 images and 5 logos. */
const DISPLAY_IMAGES = 15;
const DISPLAY_LOGOS = 5;

function DisplayAd({ draft, spec, change, problems }: StepProps) {
  const d = spec.display;
  const set = (patch: Partial<Spec["display"]>) => change("display", { ...d, ...patch });
  const website = landingOf(spec);
  const business = d.business_name.trim() || spec.assets.business_name;
  const images = d.marketing_images.length + d.square_images.length;
  const roomFor = (own: number) => DISPLAY_IMAGES - (images - own);
  const logos = d.logos.length + d.landscape_logos.length;
  const first = (values: string[]) => values.map((v) => v.trim()).find(Boolean);

  return (
    <div className="flex flex-col gap-5">
      <Problems items={problems} />
      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
        <div className="flex min-w-0 flex-col gap-5">
          <Card
            title="Responsive display ad"
            help="Google fits these assets to the ad spaces on millions of sites and apps, in the sizes and shapes each one needs."
          >
            <div className="flex flex-col gap-4 p-5 sm:p-6">
              <Text
                label="Final URL"
                type="url"
                value={d.final_url}
                placeholder={website || "https://"}
                hint={
                  d.final_url
                    ? "Where people land."
                    : `Empty uses your campaign website${website ? `, ${website}` : ""}.`
                }
                onChange={(final_url) => set({ final_url })}
              />
            </div>
          </Card>

          <Card
            title="Images"
            help={`At least 1 landscape and 1 square image. Up to ${DISPLAY_IMAGES} in all, with ${images} added so far.`}
          >
            <div className="flex flex-col gap-6 p-5 sm:p-6">
              <Images
                draftId={draft.id}
                shape="landscape"
                title="Landscape (1.91:1)"
                images={d.marketing_images}
                least={1}
                most={roomFor(d.marketing_images.length)}
                onChange={(marketing_images) => set({ marketing_images })}
              />
              <Images
                draftId={draft.id}
                shape="square"
                title="Square (1:1)"
                images={d.square_images}
                least={1}
                most={roomFor(d.square_images.length)}
                onChange={(square_images) => set({ square_images })}
              />
            </div>
          </Card>

          <Card
            title="Logos"
            help={`Optional, and recommended. Up to ${DISPLAY_LOGOS} in all, with ${logos} added so far.`}
          >
            <div className="flex flex-col gap-6 p-5 sm:p-6">
              <Images
                draftId={draft.id}
                shape="logo"
                title="Square logo (1:1)"
                images={d.logos}
                most={DISPLAY_LOGOS - d.landscape_logos.length}
                onChange={(next) => set({ logos: next })}
              />
              <Images
                draftId={draft.id}
                shape="landscape_logo"
                title="Landscape logo (4:1)"
                images={d.landscape_logos}
                most={DISPLAY_LOGOS - d.logos.length}
                onChange={(landscape_logos) => set({ landscape_logos })}
              />
            </div>
          </Card>

          <Card
            title="Headlines and descriptions"
            help="Google picks among these for each ad space."
          >
            <Section
              title="Headlines"
              help="1 to 5, up to 30 characters each. Shown in small spaces."
            >
              <Lines
                values={d.headlines}
                onChange={(headlines) => set({ headlines })}
                most={5}
                least={1}
                longest={30}
                placeholder="Headline"
                addLabel="Headline"
              />
            </Section>
            <Section
              title="Long headline"
              help="Up to 90 characters. Shown in larger spaces, and in place of a headline."
            >
              <Text
                label="Long headline"
                value={d.long_headline}
                most={90}
                placeholder="Your long headline"
                onChange={(long_headline) => set({ long_headline })}
              />
            </Section>
            <Section title="Descriptions" help="1 to 5, up to 90 characters each.">
              <Lines
                values={d.descriptions}
                onChange={(descriptions) => set({ descriptions })}
                most={5}
                least={1}
                longest={90}
                placeholder="Description"
                addLabel="Description"
              />
            </Section>
            <Section title="Business name and call to action">
              <Text
                label="Business name"
                value={d.business_name}
                most={25}
                placeholder={spec.assets.business_name || "Your business"}
                hint={
                  !d.business_name && spec.assets.business_name
                    ? `Empty uses ${spec.assets.business_name}.`
                    : "As customers know you."
                }
                onChange={(business_name) => set({ business_name })}
              />
              <div className="max-w-[420px]">
                <CtaText
                  label="Call to action text"
                  value={d.call_to_action}
                  onChange={(call_to_action) => set({ call_to_action })}
                  most={30}
                  hint="Optional, up to 30 characters. Leave it empty and Google picks one."
                />
              </div>
            </Section>
          </Card>

          <Card
            title="Videos"
            help="Optional. Google may show a video in place of an image where the ad space allows it."
          >
            <div className="p-5 sm:p-6">
              <Videos videos={d.videos} onChange={(videos) => set({ videos })} most={5} />
            </div>
          </Card>
        </div>

        <div className="flex min-w-0 flex-col gap-4 xl:sticky xl:top-6 xl:self-start">
          <DisplayPreview
            image={d.marketing_images[0]}
            square={d.square_images[0]}
            headline={first(d.headlines)}
            longHeadline={d.long_headline}
            description={first(d.descriptions)}
            logo={d.logos[0]}
            business={business}
            cta={d.call_to_action.trim() || "Learn more"}
          />
        </div>
      </div>
    </div>
  );
}

/** App images come in three shapes; the server keeps them in one list. */
function shapeOf(image: AdImage): "landscape" | "square" | "portrait" {
  const ratio = image.height ? image.width / image.height : 1;
  if (ratio > 1.3) return "landscape";
  if (ratio < 0.9) return "portrait";
  return "square";
}

const APP_IMAGES = 20;
const APP_VIDEOS = 20;

function AppAds({ draft, spec, change, problems }: StepProps) {
  const a = spec.app;
  const set = (patch: Partial<Spec["app"]>) => change("app", { ...a, ...patch });
  const room = APP_IMAGES - a.images.length;
  const byShape = (shape: ReturnType<typeof shapeOf>) =>
    a.images.filter((i) => shapeOf(i) === shape);
  // One shape's list changed: keep the other shapes as they were.
  const replaceShape = (shape: ReturnType<typeof shapeOf>, next: AdImage[]) =>
    set({ images: [...a.images.filter((i) => shapeOf(i) !== shape), ...next] });

  return (
    <div className="flex flex-col gap-5">
      <Problems items={problems} />
      <Note>
        Google reads your store listing and uses it in the ads on its own: the app&apos;s name,
        icon, screenshots, rating and description. What you add here gives Google more to work with,
        and lets your ads show in more places, such as YouTube.
      </Note>

      <Card title="Ad group">
        <div className="p-5 sm:p-6">
          <Text
            label="Ad group name"
            value={a.ad_group_name}
            placeholder="Ad group 1"
            hint="Customers never see it."
            onChange={(ad_group_name) => set({ ad_group_name })}
          />
        </div>
      </Card>

      <Card title="Text" help="Google mixes these lines into ads for each place they show.">
        <Section title="Headlines" help="1 to 5, up to 30 characters each.">
          <Lines
            values={a.headlines}
            onChange={(headlines) => set({ headlines })}
            most={5}
            least={1}
            longest={30}
            placeholder="Headline"
            addLabel="Headline"
          />
        </Section>
        <Section title="Descriptions" help="1 to 5, up to 90 characters each.">
          <Lines
            values={a.descriptions}
            onChange={(descriptions) => set({ descriptions })}
            most={5}
            least={1}
            longest={90}
            placeholder="Description"
            addLabel="Description"
          />
        </Section>
      </Card>

      <Card
        title="Images"
        help={`Optional. Up to ${APP_IMAGES} in all, with ${a.images.length} added so far. Without them, Google uses your store listing's screenshots.`}
      >
        <div className="flex flex-col gap-6 p-5 sm:p-6">
          {(["landscape", "square", "portrait"] as const).map((shape) => {
            const own = byShape(shape);
            return (
              <Images
                key={shape}
                draftId={draft.id}
                shape={shape}
                title={
                  shape === "landscape"
                    ? "Landscape (1.91:1)"
                    : shape === "square"
                      ? "Square (1:1)"
                      : "Portrait (4:5)"
                }
                images={own}
                most={own.length + room}
                onChange={(next) => replaceShape(shape, next)}
              />
            );
          })}
        </div>
      </Card>

      <Card
        title="Videos"
        help="Optional, and recommended. Videos in any shape let your ads show on YouTube. Without one, Google may make a video from your store listing."
      >
        <div className="p-5 sm:p-6">
          <Labelled label="YouTube videos">
            <Videos videos={a.videos} onChange={(videos) => set({ videos })} most={APP_VIDEOS} />
          </Labelled>
        </div>
      </Card>
    </div>
  );
}
