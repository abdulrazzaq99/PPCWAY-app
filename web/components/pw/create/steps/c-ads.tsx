"use client";

import { CardsIcon, ImageSquareIcon, PlusIcon, VideoCameraIcon } from "@phosphor-icons/react";
import { useState } from "react";
import type { DemandGenAd } from "@/lib/creation";
import { Card, Counted, Images, Labelled, Lines, type Shape } from "../kit";
import { Confirm, Pick, Quiet, Section, Segmented, Text } from "./b-form";
import { PMAX_CTAS } from "./b-options";
import { Videos } from "./b-pmax";
import { DemandGenPreview } from "./c-preview";
import { FORMAT_LABEL } from "./c-words";

/*
  One Demand Gen ad, in Google's three formats: "Image ad", "Video ad" and
  "Carousel ad". Each format asks for what the server sends for it
  (`builder/ops.py`, `_demand_gen`): images, headlines and descriptions for
  an image ad; YouTube videos with long headlines for a video ad; two to ten
  cards for a carousel. Switching format keeps what was typed, so nothing is
  lost on the way back.
*/

type CardItem = DemandGenAd["cards"][number];

const IMAGES_MOST = 20;

export function newDemandGenAd(ads: DemandGenAd[]): DemandGenAd {
  const taken = new Set(ads.map((a) => a.name.trim().toLowerCase()));
  let n = ads.length + 1;
  while (taken.has(`ad ${n}`)) n += 1;
  return {
    format: "image",
    name: `Ad ${n}`,
    final_url: "",
    headlines: [""],
    long_headlines: [],
    descriptions: [""],
    business_name: "",
    call_to_action: "",
    marketing_images: [],
    square_images: [],
    portrait_images: [],
    logos: [],
    videos: [],
    cards: [],
  };
}

const blankCard = (): CardItem => ({
  image: null,
  headline: "",
  call_to_action: "",
  final_url: "",
});

const SUGGESTED = ["Learn more", "Shop now", "Sign up", "Book now", "Get quote", "Contact us"];

/*
  The button's words, typed. Google keeps them short; a few of its usual
  ones are offered to tap. Empty lets Google choose.
*/
export function CtaText({
  label,
  value,
  onChange,
  most,
  hint,
}: {
  label: string;
  value: string;
  onChange: (next: string) => void;
  most: number;
  hint?: string;
}) {
  return (
    <Labelled label={label} hint={hint}>
      <Counted
        value={value}
        onChange={onChange}
        most={most}
        placeholder="Learn more"
        ariaLabel={label}
      />
      <span className="flex flex-wrap gap-2">
        {SUGGESTED.filter((s) => s.length <= most && s !== value).map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => onChange(s)}
            className="border-pw-border hover:border-pw-blue text-pw-ink-700 rounded-full border px-3 py-[3px] text-[12px]"
          >
            {s}
          </button>
        ))}
      </span>
    </Labelled>
  );
}

const FORMATS = [
  {
    value: "image" as const,
    label: FORMAT_LABEL.image,
    icon: <ImageSquareIcon className="size-[14px]" />,
  },
  {
    value: "video" as const,
    label: FORMAT_LABEL.video,
    icon: <VideoCameraIcon className="size-[14px]" />,
  },
  {
    value: "carousel" as const,
    label: FORMAT_LABEL.carousel,
    icon: <CardsIcon className="size-[14px]" />,
  },
];

const FORMAT_HELP: Record<DemandGenAd["format"], string> = {
  image:
    "Images with headlines and descriptions. Shows in Discover, Gmail, YouTube feeds and on the Display Network.",
  video:
    "1 to 5 YouTube videos with your words. Shows on YouTube in-stream, in-feed and Shorts, and beyond.",
  carousel: "2 to 10 cards that people swipe through, each with its own image, headline and page.",
};

export function DemandGenAdEditor({
  ad,
  at,
  onChange,
  onRemove,
  draftId,
  landing,
  businessFallback,
}: {
  ad: DemandGenAd;
  at: number;
  onChange: (next: DemandGenAd) => void;
  /** Absent for the only ad: an ad group needs at least one. */
  onRemove?: () => void;
  draftId: string;
  landing: string;
  businessFallback: string;
}) {
  const set = (patch: Partial<DemandGenAd>) => onChange({ ...ad, ...patch });
  const [removing, setRemoving] = useState(false);
  const business = ad.business_name.trim() || businessFallback;
  const url = ad.final_url.trim() || landing;
  const images = ad.marketing_images.length + ad.square_images.length + ad.portrait_images.length;
  const roomFor = (own: number) => IMAGES_MOST - (images - own);

  // A carousel needs at least two cards, so switching to it starts two.
  const pickFormat = (format: DemandGenAd["format"]) =>
    set(
      format === "carousel" && ad.cards.length < 2
        ? {
            format,
            cards: [...ad.cards, ...Array.from({ length: 2 - ad.cards.length }, blankCard)],
          }
        : { format },
    );

  const title = ad.name.trim() || `Ad ${at + 1}`;
  return (
    <Card
      title={title}
      help={FORMAT_LABEL[ad.format]}
      aside={
        onRemove ? (
          <Quiet tone="red" onClick={() => setRemoving(true)} label={`Remove ${title}`}>
            Remove ad
          </Quiet>
        ) : null
      }
    >
      {removing && onRemove ? (
        <div className="px-5 pt-4 sm:px-6">
          <Confirm
            words="Remove this ad? Its words go from the draft. Images stay in your Google Ads asset library."
            yes="Remove ad"
            // The next ad takes this one's place in the list, so the question must not stay open.
            onYes={() => {
              setRemoving(false);
              onRemove();
            }}
            onNo={() => setRemoving(false)}
          />
        </div>
      ) : null}
      <div className="grid xl:grid-cols-[minmax(0,1fr)_320px]">
        <div className="min-w-0">
          <Section title="Ad name and format">
            <Text
              label="Ad name"
              value={ad.name}
              placeholder={`Ad ${at + 1}`}
              hint="Customers never see it."
              onChange={(name) => set({ name })}
            />
            <div className="flex flex-col gap-[6px]">
              <span className="text-pw-ink text-[13px] leading-[18px] font-semibold">
                Ad format
              </span>
              <div>
                <Segmented
                  label="Ad format"
                  value={ad.format}
                  options={FORMATS}
                  onChange={pickFormat}
                />
              </div>
              <span className="text-pw-ink-500 text-[12px] leading-[16px]">
                {FORMAT_HELP[ad.format]}
              </span>
            </div>
          </Section>

          {ad.format === "image" ? (
            <Section
              title="Images"
              help={`At least 1 landscape or square image. Up to ${IMAGES_MOST} in all, with ${images} added so far.`}
            >
              <Images
                draftId={draftId}
                shape="landscape"
                title="Landscape (1.91:1)"
                images={ad.marketing_images}
                most={roomFor(ad.marketing_images.length)}
                onChange={(marketing_images) => set({ marketing_images })}
              />
              <Images
                draftId={draftId}
                shape="square"
                title="Square (1:1)"
                images={ad.square_images}
                most={roomFor(ad.square_images.length)}
                onChange={(square_images) => set({ square_images })}
              />
              <Images
                draftId={draftId}
                shape="portrait"
                title="Portrait (4:5), optional"
                images={ad.portrait_images}
                most={roomFor(ad.portrait_images.length)}
                onChange={(portrait_images) => set({ portrait_images })}
              />
            </Section>
          ) : null}

          {ad.format === "video" ? (
            <Section
              title="Videos"
              help="1 to 5 YouTube videos. Google takes videos of 5 seconds or more, but one under 10 seconds won't show on YouTube in-stream."
            >
              <Videos videos={ad.videos} onChange={(videos) => set({ videos })} most={5} />
            </Section>
          ) : null}

          {ad.format === "carousel" ? (
            <CarouselCards
              cards={ad.cards}
              onChange={(cards) => set({ cards })}
              draftId={draftId}
              url={url}
            />
          ) : null}

          <Section
            title={
              ad.format === "carousel" ? "Headline and description" : "Headlines and descriptions"
            }
            help={
              ad.format === "carousel"
                ? "Shown above the cards."
                : "Google mixes these with your images and videos for each place the ad shows."
            }
          >
            {ad.format === "carousel" ? (
              <>
                <Text
                  label="Headline"
                  value={ad.headlines[0] ?? ""}
                  most={40}
                  placeholder="Your headline"
                  onChange={(h) => set({ headlines: [h, ...ad.headlines.slice(1)] })}
                />
                <Text
                  label="Description"
                  value={ad.descriptions[0] ?? ""}
                  most={90}
                  placeholder="Your description"
                  onChange={(d) => set({ descriptions: [d, ...ad.descriptions.slice(1)] })}
                />
              </>
            ) : (
              <>
                <Labelled label="Headlines" hint="1 to 5, up to 40 characters each.">
                  <Lines
                    values={ad.headlines}
                    onChange={(headlines) => set({ headlines })}
                    most={5}
                    least={1}
                    longest={40}
                    placeholder="Headline"
                    addLabel="Headline"
                  />
                </Labelled>
                {ad.format === "video" ? (
                  <Labelled
                    label="Long headlines"
                    hint="1 to 5, up to 90 characters each. Used where there is room, such as in YouTube's feed."
                  >
                    <Lines
                      values={ad.long_headlines}
                      onChange={(long_headlines) => set({ long_headlines })}
                      most={5}
                      least={1}
                      longest={90}
                      placeholder="Long headline"
                      addLabel="Long headline"
                    />
                  </Labelled>
                ) : null}
                <Labelled label="Descriptions" hint="1 to 5, up to 90 characters each.">
                  <Lines
                    values={ad.descriptions}
                    onChange={(descriptions) => set({ descriptions })}
                    most={5}
                    least={1}
                    longest={90}
                    placeholder="Description"
                    addLabel="Description"
                  />
                </Labelled>
              </>
            )}
          </Section>

          <Section title="Business name and logo">
            <Text
              label="Business name"
              value={ad.business_name}
              most={25}
              placeholder={businessFallback || "Your business"}
              hint={
                !ad.business_name && businessFallback
                  ? `Empty uses ${businessFallback}.`
                  : "As customers know you."
              }
              onChange={(business_name) => set({ business_name })}
            />
            <Images
              draftId={draftId}
              shape="logo"
              title="Square logo (1:1)"
              images={ad.logos}
              least={1}
              // Google takes up to 5 logos on an image ad and one on the others.
              most={ad.format === "image" ? 5 : 1}
              onChange={(logos) => set({ logos })}
            />
          </Section>

          <Section title="Final URL and call to action">
            <Text
              label="Final URL"
              type="url"
              value={ad.final_url}
              placeholder={landing || "https://"}
              hint={
                ad.final_url
                  ? "Where people land."
                  : `Empty uses your campaign website${landing ? `, ${landing}` : ""}.`
              }
              onChange={(final_url) => set({ final_url })}
            />
            {ad.format === "video" ? (
              <Pick
                label="Call to action"
                hint="Automated lets Google pick the button that fits each placement."
                value={ad.call_to_action}
                options={PMAX_CTAS}
                onChange={(call_to_action) => set({ call_to_action })}
                className="max-w-[320px]"
              />
            ) : (
              <div className="max-w-[420px]">
                <CtaText
                  label="Call to action"
                  value={ad.call_to_action}
                  onChange={(call_to_action) => set({ call_to_action })}
                  most={10}
                  hint="Up to 10 characters. Leave it empty and Google picks one."
                />
              </div>
            )}
          </Section>
        </div>

        <div className="border-pw-border border-t p-5 sm:p-6 xl:border-t-0 xl:border-l">
          <div className="xl:sticky xl:top-6">
            <DemandGenPreview ad={{ ...ad, final_url: url }} business={business} />
          </div>
        </div>
      </div>
    </Card>
  );
}

/*
  A carousel's cards. Google needs every card's image in the same shape, so
  the shape is chosen once for the carousel; changing it takes off the
  images of the other shape, which Google would refuse.
*/
function CarouselCards({
  cards,
  onChange,
  draftId,
  url,
}: {
  cards: CardItem[];
  onChange: (next: CardItem[]) => void;
  draftId: string;
  url: string;
}) {
  const squareOf = (c: CardItem) => Boolean(c.image && c.image.width === c.image.height);
  const withImage = cards.find((c) => c.image);
  // The images say the shape once there are any; the choice is kept for when there are none.
  const [picked, setPicked] = useState<Shape>("square");
  const shape: Shape = withImage ? (squareOf(withImage) ? "square" : "landscape") : picked;
  const edit = (at: number, patch: Partial<CardItem>) =>
    onChange(cards.map((c, i) => (i === at ? { ...c, ...patch } : c)));
  const pickShape = (next: Shape) => {
    setPicked(next);
    const square = next === "square";
    onChange(cards.map((c) => (c.image && squareOf(c) !== square ? { ...c, image: null } : c)));
  };
  const withImages = cards.filter((c) => c.image).length;

  return (
    <Section
      title="Cards"
      help={`2 to 10 cards, ${withImages} with an image so far. Every card's image has to be the same shape.`}
    >
      <div className="flex flex-col gap-[6px]">
        <span className="text-pw-ink text-[13px] leading-[18px] font-semibold">
          Card image shape
        </span>
        <div>
          <Segmented
            label="Card image shape"
            value={shape === "landscape" ? "landscape" : "square"}
            options={[
              { value: "square", label: "Square (1:1)" },
              { value: "landscape", label: "Landscape (1.91:1)" },
            ]}
            onChange={pickShape}
          />
        </div>
        <span className="text-pw-ink-500 text-[12px] leading-[16px]">
          Changing the shape takes off the card images of the other shape.
        </span>
      </div>
      <ol className="flex flex-col gap-4">
        {cards.map((card, at) => (
          <li key={at} className="border-pw-border flex flex-col gap-4 rounded-[14px] border p-4">
            <div className="flex items-center justify-between gap-3">
              <p className="text-pw-ink text-[14px] font-semibold">Card {at + 1}</p>
              <Quiet
                tone="red"
                onClick={() => onChange(cards.filter((_, i) => i !== at))}
                disabled={cards.length <= 2}
                label={`Remove card ${at + 1}`}
              >
                Remove
              </Quiet>
            </div>
            <Images
              draftId={draftId}
              shape={shape}
              title="Card image"
              images={card.image ? [card.image] : []}
              least={1}
              most={1}
              onChange={(next) => edit(at, { image: next[0] ?? null })}
            />
            <Text
              label="Card headline"
              value={card.headline}
              most={40}
              placeholder={`Card ${at + 1} headline`}
              hint="Not shown on Discover."
              onChange={(headline) => edit(at, { headline })}
            />
            <div className="grid gap-4 sm:grid-cols-2">
              <CtaText
                label="Call to action"
                value={card.call_to_action}
                onChange={(call_to_action) => edit(at, { call_to_action })}
                most={10}
              />
              <Text
                label="Final URL (optional)"
                type="url"
                value={card.final_url}
                placeholder={url || "https://"}
                hint="Empty uses the ad's final URL."
                onChange={(final_url) => edit(at, { final_url })}
              />
            </div>
          </li>
        ))}
      </ol>
      <div className="flex items-center justify-between gap-3">
        <Quiet onClick={() => onChange([...cards, blankCard()])} disabled={cards.length >= 10}>
          <PlusIcon className="size-4" /> Add a card
        </Quiet>
        <span className="text-pw-ink-400 text-[12px]">{cards.length} of 10</span>
      </div>
    </Section>
  );
}
