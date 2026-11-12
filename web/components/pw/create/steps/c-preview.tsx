"use client";

import { ImageIcon, PlayIcon } from "@phosphor-icons/react";
import type { ReactNode } from "react";
import type { AdImage, DemandGenAd } from "@/lib/creation";
import { ctaWords } from "./c-words";

/*
  What a Demand Gen or Display ad may look like: an image ad in a feed, a
  video ad on YouTube, a carousel's cards side by side. Drawn in the browser
  from the assets typed so far, with the first of each. Google assembles the
  real ad itself, for each place it shows, so this is a likeness, not a
  promise.
*/

function Picture({ image, ratio }: { image?: AdImage | null; ratio: number }) {
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

function Who({ logo, business }: { logo?: AdImage; business: string }) {
  return (
    <span className="flex min-w-0 items-center gap-2">
      {logo?.url ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={logo.url} alt="" className="size-6 shrink-0 rounded-full object-cover" />
      ) : (
        <span
          aria-hidden
          className="bg-pw-muted text-pw-ink-600 flex size-6 shrink-0 items-center justify-center rounded-full text-[11px] font-semibold"
        >
          {(business.trim().charAt(0) || "G").toUpperCase()}
        </span>
      )}
      <span className="text-pw-ink-600 truncate text-[12px]">
        <span className="text-pw-ink font-bold">Sponsored</span> · {business || "Your business"}
      </span>
    </span>
  );
}

function Button({ words }: { words: string }) {
  return (
    <span className="bg-pw-blue shrink-0 rounded-full px-3 py-[5px] text-[12px] font-semibold text-white">
      {words}
    </span>
  );
}

const first = (values: string[]) => values.map((v) => v.trim()).find(Boolean);

/** An image ad as a feed card: the picture, the words, who it is from and the button. */
export function FeedCard({
  image,
  ratio,
  headline,
  description,
  logo,
  business,
  cta,
}: {
  image?: AdImage | null;
  ratio: number;
  headline?: string;
  description?: string;
  logo?: AdImage;
  business: string;
  cta: string;
}) {
  return (
    <div className="border-pw-border overflow-hidden rounded-[10px] border">
      <Picture image={image} ratio={ratio} />
      <div className="flex flex-col gap-1 p-3">
        <p className="text-pw-ink text-[15px] leading-[20px] font-semibold break-words">
          {headline || "Your headline"}
        </p>
        <p className="text-pw-ink-600 text-[13px] leading-[18px] break-words">
          {description || "Your description."}
        </p>
        <div className="mt-2 flex items-center justify-between gap-2">
          <Who logo={logo} business={business} />
          <Button words={cta} />
        </div>
      </div>
    </div>
  );
}

function Frame({ label, children, note }: { label: string; children: ReactNode; note: string }) {
  return (
    <section aria-label={label} className="flex flex-col gap-3">
      <h4 className="text-pw-ink text-[14px] font-semibold">Preview</h4>
      <div className="border-pw-border bg-pw-card mx-auto w-full max-w-[380px] rounded-[22px] border p-4">
        {children}
      </div>
      <p className="text-pw-ink-500 text-[12px] leading-[17px]">{note}</p>
    </section>
  );
}

/** One Demand Gen ad, drawn in the shape of its format. */
export function DemandGenPreview({ ad, business }: { ad: DemandGenAd; business: string }) {
  const logo = ad.logos[0];
  const headline = first(ad.headlines);
  const description = first(ad.descriptions);

  if (ad.format === "video") {
    const id = ad.videos[0];
    return (
      <Frame
        label="Video ad preview"
        note="A likeness of the ad in a YouTube feed. Google picks the video, words and layout for each place it shows."
      >
        <div className="flex flex-col gap-2">
          <div className="bg-pw-muted relative aspect-video overflow-hidden rounded-[10px]">
            {id ? (
              // YouTube's own thumbnail for the video.
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={`https://i.ytimg.com/vi/${id}/mqdefault.jpg`}
                alt=""
                className="size-full object-cover"
              />
            ) : null}
            <PlayIcon
              weight="fill"
              className="absolute inset-0 m-auto size-10 text-white drop-shadow"
              aria-label={id ? "Video" : "No video yet"}
            />
          </div>
          <p className="text-pw-ink text-[15px] leading-[20px] font-semibold break-words">
            {first(ad.long_headlines) || headline || "Your headline"}
          </p>
          <div className="flex items-center justify-between gap-2">
            <Who logo={logo} business={business} />
            <Button words={ctaWords(ad.call_to_action)} />
          </div>
        </div>
      </Frame>
    );
  }

  if (ad.format === "carousel") {
    const cards = ad.cards.length ? ad.cards : [null, null];
    const square = ad.cards.some((c) => c.image && c.image.width === c.image.height);
    return (
      <Frame
        label="Carousel ad preview"
        note="A likeness of the carousel in a feed. People swipe through the cards; each one opens its own page."
      >
        <div className="flex flex-col gap-2">
          <Who logo={logo} business={business} />
          <p className="text-pw-ink text-[15px] leading-[20px] font-semibold break-words">
            {headline || "Your headline"}
          </p>
          <p className="text-pw-ink-600 text-[13px] leading-[18px] break-words">
            {description || "Your description."}
          </p>
          <ul className="-mx-1 flex gap-2 overflow-x-auto px-1 pb-1">
            {cards.map((card, at) => (
              <li
                key={at}
                className="border-pw-border w-[150px] shrink-0 overflow-hidden rounded-[10px] border"
              >
                <Picture image={card?.image} ratio={square ? 1 : 1.91} />
                <div className="flex flex-col gap-2 p-2">
                  <p className="text-pw-ink line-clamp-2 text-[13px] leading-[17px] font-semibold">
                    {card?.headline.trim() || `Card ${at + 1}`}
                  </p>
                  <span className="text-pw-blue text-[12px] font-semibold">
                    {card?.call_to_action.trim() || ctaWords(ad.call_to_action)}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        </div>
      </Frame>
    );
  }

  const image = ad.marketing_images[0] ?? ad.square_images[0] ?? ad.portrait_images[0];
  const ratio = ad.marketing_images[0]
    ? 1.91
    : ad.square_images[0]
      ? 1
      : ad.portrait_images[0]
        ? 0.8
        : 1.91;
  return (
    <Frame
      label="Image ad preview"
      note="A likeness of the ad in Discover or Gmail. Google picks the image, words and layout for each place it shows."
    >
      <FeedCard
        image={image}
        ratio={ratio}
        headline={headline}
        description={description}
        logo={logo}
        business={business}
        cta={ctaWords(ad.call_to_action)}
      />
    </Frame>
  );
}

/** A responsive display ad on a site, from its first image and lines. */
export function DisplayPreview({
  image,
  square,
  headline,
  longHeadline,
  description,
  logo,
  business,
  cta,
}: {
  image?: AdImage;
  square?: AdImage;
  headline?: string;
  longHeadline: string;
  description?: string;
  logo?: AdImage;
  business: string;
  cta: string;
}) {
  return (
    <Frame
      label="Responsive display ad preview"
      note="A likeness of one size the ad may take on a site or app. Google fits your assets to thousands of ad spaces."
    >
      <div className="flex flex-col gap-4">
        <FeedCard
          image={image ?? square}
          ratio={image ? 1.91 : 1}
          headline={longHeadline.trim() || headline}
          description={description}
          logo={logo}
          business={business}
          cta={cta}
        />
        <div className="border-pw-border flex items-center gap-3 overflow-hidden rounded-[10px] border p-2">
          <div className="w-[64px] shrink-0 overflow-hidden rounded-[6px]">
            <Picture image={square ?? image} ratio={1} />
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-pw-ink truncate text-[13px] font-semibold">
              {headline || "Your short headline"}
            </p>
            <p className="text-pw-ink-500 truncate text-[12px]">{business || "Your business"}</p>
          </div>
          <Button words={cta} />
        </div>
      </div>
    </Frame>
  );
}
