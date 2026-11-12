import type { CampaignType, DemandGenAd, Setup, Spec, StepId } from "@/lib/creation";
import { money } from "../kit";
import { negativesSummary, urlSummary } from "./a-more";
import { TARGET_OPTION, locationsSummary } from "./a-locations";
import { count, customerSentence, dateWords, strategySentence } from "./a-parts";
import { scheduleSummary } from "./a-schedule";
import { CTA_LABEL, STORES } from "./b-options";

/*
  Google's words for Demand Gen, Display, Shopping and App, and the review
  page's sentences for them. Kept apart from the Search and Performance Max
  sentences in `a-parts` and `review.tsx`, so those read exactly as before.
*/

export const MORE_TYPES: CampaignType[] = ["DEMAND_GEN", "DISPLAY", "SHOPPING", "APP"];

/** Demand Gen, Display, Shopping or App: the types with their own screens here. */
export function isMore(type: CampaignType): boolean {
  return MORE_TYPES.includes(type);
}

/** Demand Gen's "Let me choose" channels, with the snake ids the server keeps. */
export const CHANNELS: { id: string; label: string; help: string }[] = [
  {
    id: "youtube_in_stream",
    label: "YouTube in-stream",
    help: "Before, during or after other videos. Video ads only.",
  },
  {
    id: "youtube_in_feed",
    label: "YouTube in-feed",
    help: "In YouTube's home feed, its search results and beside related videos.",
  },
  { id: "youtube_shorts", label: "YouTube Shorts", help: "Between Shorts, full screen on phones." },
  { id: "discover", label: "Discover", help: "In the Discover feed of the Google app." },
  { id: "gmail", label: "Gmail", help: "In the Promotions and Social tabs." },
  { id: "display", label: "Display", help: "On sites and apps in Google's Display Network." },
  {
    id: "maps",
    label: "Maps",
    help: "On Google Maps. Ads show there only when the account has a location asset.",
  },
];

export const FORMAT_LABEL: Record<DemandGenAd["format"], string> = {
  image: "Image ad",
  video: "Video ad",
  carousel: "Carousel ad",
};

type App = Spec["app"];

export const SUBTYPE_LABEL: Record<App["subtype"], string> = {
  APP_CAMPAIGN: "App installs",
  APP_CAMPAIGN_FOR_ENGAGEMENT: "App engagement",
  APP_CAMPAIGN_FOR_PRE_REGISTRATION: "App pre-registration (Android only)",
};

export const APP_FOCUS_LABEL: Record<App["focus"], string> = {
  installs: "Install volume",
  in_app_actions: "In-app actions",
  in_app_value: "In-app action value",
};

export const PRIORITY_LABEL: Record<Spec["shopping"]["priority"], string> = {
  0: "Low",
  1: "Medium",
  2: "High",
};

export const STORE_LABEL: Record<App["store"], string> = Object.fromEntries(
  STORES.map((s) => [s.value, s.label]),
) as Record<App["store"], string>;

type Devices = Spec["devices"];
export type Device = keyof Devices;

export const DEVICE_WORDS: Record<Device, string> = {
  DESKTOP: "computers",
  MOBILE: "mobile phones",
  TABLET: "tablets",
  CONNECTED_TV: "TV screens",
};

/** "a, b or c", for the devices an ad does not show on. */
function either(words: string[], last = "or"): string {
  if (words.length < 2) return words.join("");
  return `${words.slice(0, -1).join(", ")} ${last} ${words[words.length - 1]}`;
}

/** The Devices row's summary for a type that only turns devices on or off. */
export function devicesWords(devices: Devices, list: Device[]): string {
  const off = list.filter((d) => (devices[d] ?? 0) <= -100);
  return off.length ? `Not on ${either(off.map((d) => DEVICE_WORDS[d]))}` : "All devices";
}

/** The bid strategy in one plain sentence, for the four types. */
export function moreStrategySentence(spec: Spec): string {
  const b = spec.bidding;
  const cur = spec.currency;
  if (spec.type === "APP") return appStrategySentence(spec.app, cur);
  if (spec.type === "DEMAND_GEN" && b.focus === "clicks") {
    const target = spec.demand_gen.target_cpc;
    return target
      ? `Target CPC: as many clicks as Google can get at about ${money(target, cur)} each.`
      : "Maximize clicks: as many clicks as the budget allows.";
  }
  return strategySentence(spec);
}

function appStrategySentence(a: App, cur: string): string {
  if (a.subtype === "APP_CAMPAIGN_FOR_PRE_REGISTRATION") {
    return "Bids for as many pre-registrations as the budget allows.";
  }
  if (a.focus === "in_app_value") {
    return a.target_roas
      ? `Target ROAS: as much in-app action value as Google can get at a ${a.target_roas}% return on ad spend.`
      : "Bids for as much in-app action value as the budget allows.";
  }
  if (a.focus === "in_app_actions") {
    return a.target_cpa
      ? `Target cost per action: as many in-app actions as Google can get at about ${money(a.target_cpa, cur)} each.`
      : "Bids for as many in-app actions as the budget allows.";
  }
  return a.target_cpa
    ? `Target cost per install: as many installs as Google can get at about ${money(a.target_cpa, cur)} each.`
    : "Bids for as many installs as the budget allows.";
}

/** The budget in one sentence. App campaigns only take a daily budget. */
export function budgetSentence(spec: Spec): string {
  const bud = spec.budget;
  const cur = spec.currency;
  if (!(bud.amount > 0)) return "No budget set yet.";
  if (bud.type === "daily" || spec.type === "APP") {
    return `${money(bud.amount, cur)} a day on average. Google may spend up to twice that on a busy day, and never more than 30.4 times it in a month.`;
  }
  return `${money(bud.amount, cur)} in total, from ${spec.dates.start ? dateWords(spec.dates.start) : "the day it is published"} to ${spec.dates.end ? dateWords(spec.dates.end) : "an end date not set yet"}.`;
}

const filled = (values: string[]) => values.filter((v) => v.trim()).length;

/** Who sees the ads, and when: the lines every one of the four types shares. */
function reachLines(spec: Spec, setup: Setup, geoOption: boolean): string[] {
  const out = [
    geoOption
      ? `Locations: ${locationsSummary(spec.locations, setup)}. Reaches ${TARGET_OPTION[spec.locations.target_option].short}.`
      : `Locations: ${locationsSummary(spec.locations, setup)}.`,
  ];
  if (spec.type !== "SHOPPING") {
    out.push(`Languages: ${spec.languages.map((l) => l.name).join(", ") || "none chosen yet"}.`);
  }
  return out;
}

function euLine(spec: Spec): string {
  return spec.eu_political === null
    ? "EU political ads: not answered yet."
    : spec.eu_political
      ? "Has EU political ads, so its ads don't show in the European Union."
      : "Has no EU political ads.";
}

function whenLines(spec: Spec, schedule: boolean): string[] {
  const out = [
    `${spec.dates.start ? `Starts ${dateWords(spec.dates.start)}` : "Starts when published"}, ${spec.dates.end ? `ends ${dateWords(spec.dates.end)}` : "with no end date"}.`,
  ];
  if (schedule) {
    out.push(
      spec.schedule.length
        ? `Ad schedule: ${scheduleSummary(spec.schedule)}.`
        : "Runs all day, every day.",
    );
  }
  return out;
}

function urlLine(spec: Spec): string[] {
  const urls = urlSummary(spec.url_options);
  return urls !== "No options set" ? [`Campaign URL options: ${urls}.`] : [];
}

function adSentence(ad: DemandGenAd, at: number): string {
  const name = `"${ad.name.trim() || `Ad ${at + 1}`}"`;
  const logos = ad.logos.length ? "a logo" : "no logo yet";
  if (ad.format === "video") {
    return `${name}, a video ad: ${count(ad.videos.length, "video")}, ${count(filled(ad.headlines), "headline")}, ${count(filled(ad.long_headlines), "long headline")}, ${count(filled(ad.descriptions), "description")} and ${logos}.`;
  }
  if (ad.format === "carousel") {
    const pictured = ad.cards.filter((c) => c.image?.asset).length;
    return `${name}, a carousel ad: ${count(ad.cards.length, "card")}, ${pictured} with an image, and ${logos}.`;
  }
  const images = ad.marketing_images.length + ad.square_images.length + ad.portrait_images.length;
  return `${name}, an image ad: ${count(images, "image")}, ${count(filled(ad.headlines), "headline")}, ${count(filled(ad.descriptions), "description")} and ${logos}.`;
}

/** The review page's sentences for one step of a Demand Gen, Display, Shopping or App campaign. */
export function moreLines(step: StepId, spec: Spec, setup: Setup): string[] {
  const cur = spec.currency;
  const b = spec.bidding;
  const lines: string[] = [];
  const manual = b.strategy === "manual_cpc" && spec.type !== "DEMAND_GEN" && spec.type !== "APP";

  if (step === "bidding") {
    lines.push(moreStrategySentence(spec));
    if (
      spec.type === "SHOPPING" &&
      (b.new_customers !== "off" || (!manual && b.focus === "conversion_value"))
    ) {
      lines.push(customerSentence(b, cur));
    }
    lines.push(`Budget: ${budgetSentence(spec)}`);
  }

  if (step === "settings") {
    if (spec.type === "DEMAND_GEN") {
      lines.push(...reachLines(spec, setup, true));
      lines.push(
        spec.demand_gen.campaign_level_targeting
          ? "Locations and languages are set for the whole campaign. That can't go back to ad group level after publishing."
          : "Locations and languages are set on the ad group, Google's default for Demand Gen.",
      );
      lines.push(
        `Devices: ${devicesWords(spec.devices, ["DESKTOP", "MOBILE", "TABLET", "CONNECTED_TV"])}.`,
      );
      lines.push(euLine(spec));
      lines.push(...whenLines(spec, true));
      lines.push(...urlLine(spec));
    }
    if (spec.type === "DISPLAY") {
      lines.push(...reachLines(spec, setup, true));
      lines.push(euLine(spec));
      lines.push(...whenLines(spec, true));
      lines.push(
        `Devices: ${devicesWords(spec.devices, ["DESKTOP", "MOBILE", "TABLET", "CONNECTED_TV"])}.`,
      );
      lines.push(...urlLine(spec));
    }
    if (spec.type === "SHOPPING") {
      const sh = spec.shopping;
      lines.push(
        sh.merchant_id
          ? `Sells products from Merchant Center account ${sh.merchant_id}${sh.feed_label.trim() ? `, feed label "${sh.feed_label.trim()}"` : ""}.`
          : "No Merchant Center account chosen yet.",
      );
      lines.push(
        `Campaign priority ${PRIORITY_LABEL[sh.priority].toLowerCase()}. Local inventory ads ${sh.enable_local ? "on" : "off"}.`,
      );
      lines.push(
        spec.networks.search_partners
          ? "Shows on Google Search and search partners."
          : "Shows on Google Search only.",
      );
      lines.push(...reachLines(spec, setup, false));
      lines.push(euLine(spec));
      lines.push(...whenLines(spec, true));
      lines.push(...urlLine(spec));
      lines.push(`${negativesSummary(spec.negatives, 0)}.`);
    }
    if (spec.type === "APP") {
      const a = spec.app;
      lines.push(
        a.app_id.trim()
          ? `Promotes ${a.app_id.trim()} from ${STORE_LABEL[a.store]}.`
          : "No app chosen yet.",
      );
      lines.push(`Campaign subtype: ${SUBTYPE_LABEL[a.subtype]}.`);
      if (a.subtype === "APP_CAMPAIGN_FOR_ENGAGEMENT") {
        const lists = spec.audiences.segments.filter((s) => s.kind === "user_list").length;
        lines.push(
          lists
            ? `Shows only to people on ${count(lists, "list")} of your app's users.`
            : "No list of your app's users chosen yet.",
        );
      }
      lines.push(...reachLines(spec, setup, false));
      lines.push(euLine(spec));
      lines.push(...whenLines(spec, false));
    }
  }

  if (step === "ad_group") {
    if (spec.type === "DEMAND_GEN") {
      const dg = spec.demand_gen;
      lines.push(`${dg.ad_group_name.trim() || "Ad group 1"}.`);
      const chosen = CHANNELS.filter((c) => dg.selected.includes(c.id)).map((c) => c.label);
      lines.push(
        dg.channels === "all"
          ? "Shows on all Google channels."
          : chosen.length
            ? `Shows only on ${either(chosen, "and")}.`
            : "No channel chosen yet.",
      );
      lines.push(
        `Optimized targeting ${dg.optimized_targeting ? "on" : "off"}. ${dg.segments.length ? `${count(dg.segments.length, "audience segment")}.` : "No audience segments."}`,
      );
    }
    if (spec.type === "DISPLAY") {
      const d = spec.display;
      lines.push(`${d.ad_group_name.trim() || "Ad group 1"}.`);
      const out = d.segments.filter((s) => s.excluded).length;
      const segments = [
        d.segments.length - out ? count(d.segments.length - out, "audience segment") : "",
        out ? `${count(out, "segment")} excluded` : "",
      ].filter(Boolean);
      lines.push(
        `Optimized targeting ${d.optimized_targeting ? "on" : "off"}. ${segments.length ? `${segments.join(", ")}.` : "No audience segments."}`,
      );
      lines.push(
        d.keywords.length ? `${count(d.keywords.length, "content keyword")}.` : "No keywords.",
      );
      if (manual) {
        const bid = d.default_bid ?? b.default_bid;
        lines.push(bid ? `Default bid ${money(bid, cur)} a click.` : "No default bid set yet.");
      }
    }
    if (spec.type === "SHOPPING") {
      const sh = spec.shopping;
      lines.push(`${sh.ad_group_name.trim() || "Ad group 1"}.`);
      lines.push("One product group, All products, with ads built from your product data.");
      if (manual) {
        const bid = sh.default_bid ?? b.default_bid;
        lines.push(bid ? `Bid ${money(bid, cur)} a click.` : "No bid set yet.");
      }
    }
  }

  if (step === "ads") {
    if (spec.type === "DEMAND_GEN") {
      const ads = spec.demand_gen.ads;
      if (!ads.length) lines.push("No ads yet.");
      ads.slice(0, 6).forEach((ad, at) => lines.push(adSentence(ad, at)));
      if (ads.length > 6) lines.push(`And ${count(ads.length - 6, "more ad")}.`);
    }
    if (spec.type === "DISPLAY") {
      const d = spec.display;
      const images = d.marketing_images.length + d.square_images.length;
      lines.push(
        `One responsive display ad, sending people to ${d.final_url.trim() || spec.ways.website_url || "a final URL not set yet"}.`,
      );
      lines.push(
        `${count(filled(d.headlines), "short headline")}, ${d.long_headline.trim() ? "a long headline" : "no long headline yet"} and ${count(filled(d.descriptions), "description")}.`,
      );
      lines.push(
        `${count(images, "image")}, ${count(d.logos.length + d.landscape_logos.length, "logo")} and ${count(d.videos.length, "video")}.`,
      );
      if (d.call_to_action.trim()) lines.push(`Call to action: ${d.call_to_action.trim()}.`);
    }
    if (spec.type === "APP") {
      const a = spec.app;
      lines.push(`${a.ad_group_name.trim() || "Ad group 1"}.`);
      lines.push(
        `${count(filled(a.headlines), "headline")}, ${count(filled(a.descriptions), "description")}, ${count(a.images.length, "image")} and ${count(a.videos.length, "video")}. Google adds what is in your store listing.`,
      );
    }
  }

  return lines.length ? lines : ["Nothing to show for this step."];
}

/** The button's words in a preview: Google's label for an enum value, or the text typed. */
export function ctaWords(value: string): string {
  return CTA_LABEL[value] ?? (value.trim() || "Learn more");
}
