import type { AdText, Keyword, Pin, SearchAd, Sitelink, Spec } from "@/lib/creation";

/*
  Ad Strength, estimated before the ad exists.

  Google rates an ad only once it is created (ad_group_ad.ad_strength reads
  PENDING until then), so a creation screen cannot ask for it. What Google
  does publish is what it looks at (Help 9921843 for responsive search ads,
  14143250 for Performance Max): how many headlines and descriptions, how
  different they are from each other, whether popular keywords appear whole
  in headlines, sitelinks at any level, pinning, and, for Performance Max,
  every asset type with videos in three shapes. This scores those factors
  and gives Google's five labels. The weights are PPCWay's; the screen says
  it is an estimate and that Google shows its own rating after publishing.
*/

export type Label = "Incomplete" | "Poor" | "Average" | "Good" | "Excellent";
export type Rating = { label: Label; score: number; fixes: string[] };

const plural = (n: number, one: string, many = `${one}s`) => `${n} ${n === 1 ? one : many}`;

function words(text: string): string[] {
  return text.toLowerCase().match(/[\p{L}\p{N}]+/gu) ?? [];
}

/** Two lines are near-copies when most of the shorter one's words are in the other. */
function similar(a: string, b: string): boolean {
  const x = new Set(words(a));
  const y = new Set(words(b));
  if (!x.size || !y.size) return false;
  let shared = 0;
  for (const w of x) if (y.has(w)) shared += 1;
  return shared / Math.min(x.size, y.size) >= 0.75;
}

/** The share of lines that are not near-copies of an earlier one. */
export function uniqueness(lines: string[]): number {
  if (!lines.length) return 1;
  let unique = 0;
  lines.forEach((line, at) => {
    if (!lines.slice(0, at).some((earlier) => similar(earlier, line))) unique += 1;
  });
  return unique / lines.length;
}

/** Google counts a keyword in a headline only when the whole keyword is there. */
export function hasWhole(headline: string, keyword: string): boolean {
  const k = words(keyword).join(" ");
  return k.length > 0 && ` ${words(headline).join(" ")} `.includes(` ${k} `);
}

function labelOf(score: number): Exclude<Label, "Incomplete"> {
  if (score >= 85) return "Excellent";
  if (score >= 70) return "Good";
  if (score >= 45) return "Average";
  return "Poor";
}

const filled = (lines: AdText[]) => lines.map((l) => l.text.trim()).filter(Boolean);
const isUrl = (url: string) => /^https?:\/\/\S+\.\S+/.test(url.trim());
const liveLinks = (links: Sitelink[]) => links.filter((s) => s.text.trim()).length;

/*
  Pinning: Google says it "can affect ad strength". One line pinned alone to
  a position costs the most, because that position can then only ever say
  one thing; two or three pinned to the same position cost less.
*/
function pinCost(lines: AdText[]): number {
  const at = new Map<Pin, number>();
  for (const line of lines) {
    if (line.pin && line.text.trim()) at.set(line.pin, (at.get(line.pin) ?? 0) + 1);
  }
  let cost = 0;
  for (const n of at.values()) cost += n === 1 ? 8 : 3;
  return Math.min(cost, 24);
}

export function searchStrength({
  ad,
  keywords,
  landing,
  sitelinks,
}: {
  ad: SearchAd;
  keywords: Keyword[];
  landing: string;
  sitelinks: Sitelink[];
}): Rating {
  const heads = filled(ad.headlines);
  const descs = filled(ad.descriptions);
  const live = keywords.filter((k) => k.text.trim());
  const missing: string[] = [];
  if (!isUrl(ad.final_url || landing)) missing.push("Add a final URL, the page people land on.");
  if (!live.length) missing.push("Add keywords to this ad group. Google rates an ad against them.");
  if (heads.length < 3)
    missing.push(`Add ${plural(3 - heads.length, "more headline")}. An ad needs at least 3.`);
  if (descs.length < 2)
    missing.push(`Add ${plural(2 - descs.length, "more description")}. An ad needs at least 2.`);
  if (missing.length) return { label: "Incomplete", score: 0, fixes: missing };

  const withKeyword = heads.filter((h) => live.some((k) => hasWhole(h, k.text))).length;
  const links = liveLinks(sitelinks);
  const headUnique = uniqueness(heads);
  const descUnique = uniqueness(descs);
  const pins = pinCost([...ad.headlines, ...ad.descriptions]);

  // Uniqueness means little with three lines, so it counts more as lines are added.
  const score =
    (Math.min(heads.length, 15) / 15) * 30 +
    (Math.min(descs.length, 4) / 4) * 15 +
    (headUnique * 0.7 + descUnique * 0.3) * 15 * (Math.min(heads.length, 8) / 8) +
    [0, 10, 18, 25][Math.min(withKeyword, 3)] +
    (links >= 6 ? 15 : links >= 4 ? 9 : links >= 2 ? 5 : 0) -
    pins;

  const fixes: string[] = [];
  if (heads.length < 15)
    fixes.push(
      `Add ${plural(15 - heads.length, "more headline")}. Google allows 15 and has more to mix.`,
    );
  if (withKeyword < 3) {
    const absent = live.find((k) => !heads.some((h) => hasWhole(h, k.text)));
    fixes.push(
      `Put your keywords in more headlines, whole.${absent ? ` Try one with "${absent.text}" in it.` : ""}`,
    );
  }
  if (headUnique < 0.9) fixes.push("Make headlines more unique. Some say nearly the same thing.");
  if (descs.length < 4)
    fixes.push(`Add ${plural(4 - descs.length, "more description")}. Google allows 4.`);
  if (descUnique < 1) fixes.push("Make descriptions more unique.");
  if (links < 6)
    fixes.push(
      links
        ? `Add ${plural(6 - links, "more sitelink")} under Assets to reach the 6 Google recommends.`
        : "Add sitelinks under Assets. Google counts them toward Ad Strength and recommends at least 6.",
    );
  if (pins)
    fixes.push(
      "Pin less. A line pinned alone lowers Ad Strength; if you must pin, pin 2 or 3 lines to the same position.",
    );

  const rounded = Math.max(0, Math.min(100, Math.round(score)));
  return { label: labelOf(rounded), score: rounded, fixes };
}

type Group = Spec["pmax"]["asset_group"];

export function pmaxStrength({
  group,
  businessName,
  landing,
  campaignSitelinks,
}: {
  group: Group;
  businessName: string;
  landing: string;
  campaignSitelinks: Sitelink[];
}): Rating {
  const heads = group.headlines.map((h) => h.trim()).filter(Boolean);
  const longs = group.long_headlines.map((h) => h.trim()).filter(Boolean);
  const descs = group.descriptions.map((d) => d.trim()).filter(Boolean);
  const videos = group.videos.filter((v) => v.trim()).length;
  const links = liveLinks([...campaignSitelinks, ...group.sitelinks]);
  const land = group.marketing_images.length;
  const square = group.square_images.length;
  const portrait = group.portrait_images.length;
  const wideLogo = group.landscape_logos.length;

  const missing: string[] = [];
  if (!isUrl(group.final_url || landing)) missing.push("Add a final URL.");
  if (heads.length < 3)
    missing.push(`Add ${plural(3 - heads.length, "more headline")}. Google needs 3.`);
  if (longs.length < 1) missing.push("Add a long headline.");
  if (descs.length < 2)
    missing.push(`Add ${plural(2 - descs.length, "more description")}. Google needs 2.`);
  if (descs.length && !descs.some((d) => d.length <= 60))
    missing.push("Make one description 60 characters or fewer.");
  if (!land) missing.push("Add a landscape image.");
  if (!square) missing.push("Add a square image.");
  if (!group.logos.length) missing.push("Add a square logo.");
  if (!businessName.trim()) missing.push("Add your business name.");
  if (missing.length) return { label: "Incomplete", score: 0, fixes: missing };

  const score =
    (Math.min(heads.length, 15) / 15) * 15 +
    (Math.min(longs.length, 5) / 5) * 10 +
    (Math.min(descs.length, 5) / 5) * 10 +
    (Math.min(land, 4) / 4) * 8 +
    (Math.min(square, 4) / 4) * 8 +
    (Math.min(portrait, 2) / 2) * 4 +
    3 +
    (wideLogo ? 2 : 0) +
    (Math.min(videos, 3) / 3) * 15 +
    (Math.min(links, 6) / 6) * 10 +
    uniqueness(heads) * 10 * (Math.min(heads.length, 8) / 8) +
    (heads.some((h) => h.length <= 15) ? 5 : 0);

  // Google: Excellent needs every asset type, 6+ sitelinks, videos in three
  // orientations, 15 headlines and 5 descriptions. Short of that, Good at best.
  const everything =
    heads.length >= 15 &&
    descs.length >= 5 &&
    links >= 6 &&
    videos >= 3 &&
    portrait > 0 &&
    wideLogo > 0;

  const fixes: string[] = [];
  if (heads.length < 15) fixes.push(`Add ${plural(15 - heads.length, "more headline")}, up to 15.`);
  if (!heads.some((h) => h.length <= 15))
    fixes.push("Make one headline 15 characters or fewer, as Google asks.");
  if (longs.length < 5)
    fixes.push(`Add ${plural(5 - longs.length, "more long headline")}, up to 5.`);
  if (descs.length < 5) fixes.push(`Add ${plural(5 - descs.length, "more description")}, up to 5.`);
  if (land < 4 || square < 4) fixes.push("Add 4 or more landscape and 4 or more square images.");
  if (!portrait) fixes.push("Add a portrait image (4:5).");
  if (!wideLogo) fixes.push("Add a landscape logo (4:1).");
  if (videos < 3)
    fixes.push(
      videos
        ? "Add videos so there is one horizontal, one square and one vertical."
        : "Add your own videos: one horizontal, one square and one vertical. Without any, Google may make one.",
    );
  if (links < 6)
    fixes.push(
      links ? `Add ${plural(6 - links, "more sitelink")} to reach 6.` : "Add at least 6 sitelinks.",
    );
  if (uniqueness(heads) < 0.9) fixes.push("Make headlines more unique.");

  const rounded = Math.max(0, Math.min(100, Math.round(score)));
  const label = labelOf(rounded);
  return {
    label: label === "Excellent" && !everything ? "Good" : label,
    score: rounded,
    fixes,
  };
}
