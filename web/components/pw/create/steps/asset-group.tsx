"use client";

import { CheckCircleIcon, CircleIcon } from "@phosphor-icons/react";
import type { ReactNode } from "react";
import { cn } from "@/lib/cn";
import { LIMITS, type Spec } from "@/lib/creation";
import type { StepProps } from "../editor";
import { Card, Chips, Images, Lines, Note, Problems } from "../kit";
import { DisplayPath, Pick, Section, Text } from "./b-form";
import { StrengthMeter } from "./b-meter";
import { PMAX_CTAS } from "./b-options";
import { AudienceSignal, Videos } from "./b-pmax";
import { PmaxPreview } from "./b-preview";
import { Sitelinks } from "./b-sitelinks";
import { pmaxStrength } from "./b-strength";

/*
  Google's Performance Max step 4, "Asset group": the one asset group a new
  campaign gets before publishing (more are added later in Google Ads). Its
  final URL, images, logos, videos, text, call to action and sitelinks are
  what Google builds every ad from, on every channel; its signals tell
  Google whom to look for first. With brand guidelines on, the business name
  and logos go on the campaign instead, as Google has done since April 2026.
*/

type Group = Spec["pmax"]["asset_group"];

/** Google caps images at 20 across the three shapes, and logos at 5 across both. */
const IMAGES_MOST = 20;
const LOGOS_MOST = 5;

function Rule({ met, children }: { met: boolean; children: ReactNode }) {
  const Icon = met ? CheckCircleIcon : CircleIcon;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 text-[12px]",
        met ? "text-pw-good-ink" : "text-pw-ink-500",
      )}
    >
      <Icon weight={met ? "fill" : "regular"} className="size-[14px]" aria-hidden />
      {children}
      <span className="sr-only">{met ? " (done)" : " (not yet)"}</span>
    </span>
  );
}

export function StepAssetGroup({ draft, spec, change, problems }: StepProps) {
  const pm = spec.pmax;
  const g = pm.asset_group;
  const set = (patch: Partial<Group>) => change("pmax", { ...pm, asset_group: { ...g, ...patch } });
  const website = spec.ways.website_url || spec.generation.url;
  const landing = g.final_url || website;
  const brand = pm.brand_guidelines.enabled;
  const business = g.business_name || spec.assets.business_name;

  const images = g.marketing_images.length + g.square_images.length + g.portrait_images.length;
  const roomFor = (own: number) => IMAGES_MOST - (images - own);
  const logos = g.logos.length + g.landscape_logos.length;
  const heads = g.headlines.map((h) => h.trim()).filter(Boolean);
  const descs = g.descriptions.map((d) => d.trim()).filter(Boolean);
  const rating = pmaxStrength({
    group: g,
    businessName: business,
    landing,
    campaignSitelinks: spec.assets.sitelinks,
  });

  return (
    <div className="flex flex-col gap-5">
      <Problems items={problems} />
      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
        <div className="flex min-w-0 flex-col gap-5">
          <Card
            title="Asset group"
            help="Google builds every Performance Max ad, on Search, YouTube, Display, Discover, Gmail and Maps, from this group's assets. A new campaign starts with one; you can add more in Google Ads after publishing."
          >
            <div className="flex flex-col gap-4 p-5 sm:p-6">
              <Text
                label="Asset group name"
                value={g.name}
                placeholder="Asset group 1"
                hint="Customers never see it."
                onChange={(name) => set({ name })}
              />
              <Text
                label="Final URL"
                type="url"
                value={g.final_url}
                placeholder={website || "https://"}
                hint={
                  (g.final_url
                    ? "Where people land."
                    : `Empty uses your campaign website${website ? `, ${website}` : ""}.`) +
                  (pm.final_url_expansion
                    ? " Final URL expansion is on, so Google may send people to a more relevant page on your site."
                    : "")
                }
                onChange={(final_url) => set({ final_url })}
              />
              <DisplayPath
                url={landing}
                path1={g.path1}
                path2={g.path2}
                onChange={(p) => set({ path1: p.path1, path2: p.path2 })}
              />
            </div>
          </Card>

          <Card
            title="Images"
            help={`At least 1 landscape and 1 square image; Google recommends 4 or more of each. Up to ${IMAGES_MOST} in all, with ${images} added so far.`}
          >
            <div className="flex flex-col gap-6 p-5 sm:p-6">
              <Images
                draftId={draft.id}
                shape="landscape"
                title="Landscape (1.91:1)"
                images={g.marketing_images}
                least={1}
                most={roomFor(g.marketing_images.length)}
                onChange={(marketing_images) => set({ marketing_images })}
              />
              <Images
                draftId={draft.id}
                shape="square"
                title="Square (1:1)"
                images={g.square_images}
                least={1}
                most={roomFor(g.square_images.length)}
                onChange={(square_images) => set({ square_images })}
              />
              <Images
                draftId={draft.id}
                shape="portrait"
                title="Portrait (4:5), optional"
                images={g.portrait_images}
                most={roomFor(g.portrait_images.length)}
                onChange={(portrait_images) => set({ portrait_images })}
              />
            </div>
          </Card>

          <Card
            title={brand ? "Brand guidelines: business name and logos" : "Business name and logos"}
            help={
              brand
                ? "Brand guidelines are on for this campaign, so your business name and logos go on the campaign and every asset group uses them."
                : "Brand guidelines are off, so your business name and logos belong to this asset group."
            }
          >
            <div className="flex flex-col gap-6 p-5 sm:p-6">
              <Text
                label="Business name"
                value={g.business_name}
                most={LIMITS.businessName}
                placeholder={spec.assets.business_name || "Your business"}
                hint={
                  !g.business_name && spec.assets.business_name
                    ? `Empty uses ${spec.assets.business_name}. It must match your domain or your verified legal name.`
                    : "It must match your domain or your verified legal name."
                }
                onChange={(business_name) => set({ business_name })}
              />
              <Images
                draftId={draft.id}
                shape="logo"
                title="Square logo (1:1)"
                images={g.logos}
                least={1}
                most={LOGOS_MOST - g.landscape_logos.length}
                onChange={(next) => set({ logos: next })}
              />
              <Images
                draftId={draft.id}
                shape="landscape_logo"
                title="Landscape logo (4:1), optional"
                images={g.landscape_logos}
                most={LOGOS_MOST - g.logos.length}
                onChange={(landscape_logos) => set({ landscape_logos })}
              />
              <p className="text-pw-ink-500 text-[12px]">
                {logos} of {LOGOS_MOST} logos, square and landscape together.
              </p>
            </div>
          </Card>

          <Card
            title="Videos"
            help="Optional. With no video, Google may make one from your images. Add one horizontal (16:9), one square (1:1) and one vertical (9:16) to keep that from happening and to reach Excellent."
          >
            <div className="p-5 sm:p-6">
              <Videos videos={g.videos} onChange={(videos) => set({ videos })} />
            </div>
          </Card>

          <Card
            title="Headlines and descriptions"
            help="Google mixes these with your images and videos into ads for every channel."
          >
            <Section
              title="Headlines"
              help="3 to 15, up to 30 characters each. Google asks for one of 15 characters or fewer."
            >
              <Lines
                values={g.headlines}
                onChange={(headlines) => set({ headlines })}
                most={LIMITS.headlinesMost}
                least={3}
                longest={LIMITS.headline}
                placeholder="Headline"
                addLabel="Headline"
              />
              <Rule met={heads.some((h) => h.length <= 15)}>
                One headline of 15 characters or fewer
              </Rule>
            </Section>
            <Section
              title="Long headlines"
              help="1 to 5, up to 90 characters each. Used where there is room, such as above an image."
            >
              <Lines
                values={g.long_headlines}
                onChange={(long_headlines) => set({ long_headlines })}
                most={LIMITS.longHeadlinesMost}
                least={1}
                longest={LIMITS.longHeadline}
                placeholder="Long headline"
                addLabel="Long headline"
              />
            </Section>
            <Section
              title="Descriptions"
              help="2 to 5, up to 90 characters each. One must be 60 characters or fewer."
            >
              <Lines
                values={g.descriptions}
                onChange={(descriptions) => set({ descriptions })}
                most={LIMITS.pmaxDescriptionsMost}
                least={2}
                longest={LIMITS.description}
                placeholder="Description"
                addLabel="Description"
              />
              <Rule met={descs.some((d) => d.length <= 60)}>
                One description of 60 characters or fewer
              </Rule>
            </Section>
            <Section
              title="Call to action"
              help="Automated lets Google pick the button that fits each ad best."
            >
              <Pick
                label="Call to action"
                value={g.call_to_action}
                options={PMAX_CTAS}
                onChange={(call_to_action) => set({ call_to_action })}
                className="max-w-[320px]"
              />
            </Section>
          </Card>

          <Card
            title="Sitelinks"
            help="Links to other pages of your site, shown with your ads where there is room."
          >
            <div className="p-5 sm:p-6">
              <Sitelinks
                links={g.sitelinks}
                onChange={(sitelinks) => set({ sitelinks })}
                landing={landing}
              />
            </div>
          </Card>

          <Card
            title="Signals"
            help="Optional hints that help Google find the right people sooner. Performance Max may still show ads to people outside them."
          >
            <Section
              title="Search themes"
              help={`Words and phrases people search for when they want what you sell. Up to ${LIMITS.searchThemes}. They count like phrase and broad keywords in a Search campaign; negative keywords still apply.`}
            >
              <Chips
                values={g.search_themes}
                onChange={(search_themes) => set({ search_themes })}
                most={LIMITS.searchThemes}
                longest={80}
                placeholder="A search, such as: running shoes"
                ariaLabel="Add a search theme"
              />
              <p className="text-pw-ink-400 text-[12px]">
                {g.search_themes.length} of {LIMITS.searchThemes}
              </p>
            </Section>
            <Section
              title="Audience signal"
              help="Segments of people likely to buy; your customer lists and website visitors work best. A list needs enough active members before Google can use it."
            >
              <AudienceSignal signal={g.signal} onChange={(signal) => set({ signal })} />
            </Section>
          </Card>
        </div>

        <div className="flex min-w-0 flex-col gap-4 xl:sticky xl:top-6 xl:self-start">
          <StrengthMeter
            rating={rating}
            note="PPCWay's estimate of Google's Ad Strength for this asset group. Google shows its own after publishing. At Poor, ads show on only some placements; at Average or better they can show everywhere."
          />
          <PmaxPreview group={{ ...g, final_url: landing }} business={business} />
          {rating.label !== "Incomplete" && !g.videos.length ? (
            <Note>With no video added, Google may make one from your images.</Note>
          ) : null}
        </div>
      </div>
    </div>
  );
}
