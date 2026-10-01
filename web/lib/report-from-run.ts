import type { AuditLine, AuditPanel, AuditSample } from "@/components/audit/report-views";
import type { Listing } from "./listing";

/*
  One real run, drawn as the report's cards. Every line here comes from something
  measured: the website checks from our own crawl, the listing and the comparison
  from Google Maps. Nothing is estimated, so a run with no listing simply shows
  fewer cards rather than inventing one.

  What is deliberately missing: their ads. That card stays locked, because only
  the account owner can open it.
*/
export type RunFinding = {
  key: string;
  title: string;
  status: "good" | "needs_you" | "ours" | "unknown";
  summary: string;
  detail: string[];
  fix: string | null;
  group: "checks" | "more";
};
export type Run = {
  id: string;
  site: string;
  place_id?: string;
  city?: string;
  /** What the run is doing now, while it runs. */
  stage?: string;
  pages_read?: number;
  report: {
    site: string;
    business_name: string;
    pages_read: number;
    findings: RunFinding[];
    headline: string;
  } | null;
};

/** Tracking is the money check: with it missing, every other click is bought blind. */
const COSTLY = new Set(["counting", "tags"]);
const WORDS = ["no", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"];
const say = (n: number) => WORDS[n] ?? String(n);
const plural = (n: number, one: string, many: string) => `${say(n)} ${n === 1 ? one : many}`;
/** Sentences built from counted words still start with a capital letter. */
const upper = (text: string) => text.charAt(0).toUpperCase() + text.slice(1);

function scoreOf(lines: AuditLine[]): string {
  const good = lines.filter((l) => l.verdict === "good").length;
  return `${Math.round((good / Math.max(lines.length, 1)) * 10)} of 10`;
}

/** The website checks, in the words the audit already wrote. */
function websitePanel(findings: RunFinding[]): AuditPanel {
  const lines: AuditLine[] = findings
    .filter((f) => f.status !== "unknown")
    .map((f) => ({
      title: f.title,
      meta: f.summary,
      verdict:
        f.status === "good" ? "good" : COSTLY.has(f.key) && f.status !== "ours" ? "cost" : "fix",
      ...(f.status === "good"
        ? {}
        : { who: f.status === "ours" ? ("us" as const) : ("you" as const) }),
    }));
  return { title: "Your website", score: scoreOf(lines), lines };
}

/** The Google listing, read again from Maps rather than from anything we stored. */
function listingPanel(mine: Listing, rivals: Listing[]): AuditPanel {
  const lines: AuditLine[] = [];
  const photoAverage = rivals.length
    ? Math.round(rivals.reduce((a, r) => a + r.photos, 0) / rivals.length)
    : 0;
  const nightOwls = rivals.filter((r) => r.open_24h).length;

  if (mine.reviews === 0) {
    lines.push({
      title: "No reviews yet",
      meta: rivals.length
        ? `The ${say(rivals.length)} nearest ${mine.category.toLowerCase() || "businesses"} average ${Math.round(rivals.reduce((a, r) => a + r.reviews, 0) / rivals.length)}. Reviews are the first thing people compare.`
        : "Reviews are the first thing people compare, and the hardest thing to buy.",
      verdict: "cost",
      who: "you",
    });
  } else {
    const ahead = rivals.filter((r) => r.reviews < mine.reviews).length;
    lines.push({
      title: `${mine.rating} out of 5, from ${mine.reviews} reviews`,
      meta: !rivals.length
        ? "That is the expensive thing to build, and you already have it."
        : ahead === 0
          ? `Every one of your ${say(rivals.length)} competitors has more, and reviews are the slowest thing to build.`
          : `Ahead of ${say(ahead)} of your ${say(rivals.length)} competitors.`,
      verdict: "good",
    });
  }

  if (mine.photos === 0) {
    lines.push({
      title: "No photos on your listing",
      meta: photoAverage
        ? `Your competitors carry about ${photoAverage}. Photos cost nothing and they move the Maps ranking.`
        : "Photos cost nothing and they move the Maps ranking.",
      verdict: "cost",
      who: "you",
    });
  } else if (mine.photos < 10) {
    lines.push({
      title: `${mine.photos} ${mine.photos === 1 ? "photo" : "photos"} on your listing`,
      meta: photoAverage
        ? `Your competitors carry about ${photoAverage}.`
        : "Listings with more photos are picked more often.",
      verdict: "fix",
      who: "you",
    });
  } else {
    lines.push({
      title: "Ten or more photos",
      meta: "This is the part most listings get wrong, and you have it.",
      verdict: "good",
    });
  }

  if (!mine.hours_set) {
    lines.push({
      title: "No opening hours on your listing",
      meta: "Google hides businesses with no hours from some searches, and people will not ring a business that might be shut.",
      verdict: "cost",
      who: "you",
    });
  } else if (nightOwls > 0 && !mine.open_24h) {
    lines.push({
      title: "Your listing closes; theirs do not",
      meta: `${plural(nightOwls, "business", "businesses")} nearby are open twenty four hours, so Google sends them the night calls.`,
      verdict: "fix",
      who: "you",
    });
  } else {
    lines.push({
      title: mine.open_24h ? "Open twenty four hours" : "Opening hours are set",
      meta: mine.open_24h
        ? "The night calls can reach you, which is where the expensive jobs are."
        : "People can see when you answer, which is what Google wants before it shows you.",
      verdict: "good",
    });
  }

  if (!mine.website) {
    lines.push({
      title: "No website link on your listing",
      meta: "Every person who looks you up on Maps is one tap from your site, and that tap is missing.",
      verdict: "cost",
      who: "you",
    });
  }
  if (!mine.phone) {
    lines.push({
      title: "No phone number on your listing",
      meta: "The call button is the cheapest thing on Google, and yours is not there.",
      verdict: "fix",
      who: "you",
    });
  }
  if (mine.category) {
    lines.push({
      title: `${mine.category}, the category people search`,
      meta: "Half the listings we check sit under a category nobody types.",
      verdict: "good",
    });
  } else {
    lines.push({
      title: "No category on your listing",
      meta: "Google matches searches to categories first. Without one, you are hard to find at all.",
      verdict: "cost",
      who: "you",
    });
  }

  return { title: "Your Google listing", score: scoreOf(lines), lines };
}

/** How they sit beside the same trade nearby. Maps only: never who advertises. */
function comparePanel(mine: Listing, rivals: Listing[]): AuditPanel {
  const trade = (mine.category || "business").toLowerCase();
  const betterReviews = rivals.filter((r) => r.reviews > mine.reviews).length;
  const betterRating = rivals.filter((r) => (r.rating ?? 0) > (mine.rating ?? 0)).length;
  const morePhotos = rivals.filter((r) => r.photos > mine.photos).length;
  const nightOwls = rivals.filter((r) => r.open_24h).length;
  const lines: AuditLine[] = [];

  if (betterReviews > 0) {
    lines.push({
      title: upper(
        `${plural(betterReviews, `${trade} has`, `${trade}s have`)} more reviews than you`,
      ),
      meta: "Reviews decide who gets rung first, and they are the slowest thing to build.",
      verdict: "fix",
      who: "you",
    });
  } else {
    lines.push({
      title: `You have more reviews than every competitor nearby`,
      meta: "That is the expensive thing to build, and you already have it.",
      verdict: "good",
    });
  }
  if (nightOwls > 0 && !mine.open_24h) {
    lines.push({
      title: upper(`${plural(nightOwls, "of them is", "of them are")} open twenty four hours`),
      meta: "Nights and weekends are when the urgent jobs happen, and when nobody is answering yours.",
      verdict: "fix",
      who: "you",
    });
  }
  if (morePhotos > 0) {
    lines.push({
      title: upper(`${plural(morePhotos, "of them has", "of them have")} more photos than you`),
      meta: "Photos are free, and the listing with more of them gets the tap.",
      verdict: "fix",
      who: "you",
    });
  }
  if (betterRating === 0 && mine.rating !== null) {
    lines.push({
      title: `Yours is the best rating of the ${say(rivals.length + 1)}`,
      meta: `${mine.rating} out of 5, against everyone within fifteen kilometres.`,
      verdict: "good",
    });
  }
  return { title: "Your competitors", score: "For information", lines };
}

function costOf(lines: AuditLine[], site: string): AuditSample["cost"] {
  const worst = lines.find((l) => l.verdict === "cost");
  if (!worst) return undefined;
  return {
    basis: "From your own site and listing",
    title: `${worst.title}.`,
    daily: "That is every day, and every click you pay for while it stays that way.",
    body: `${worst.meta} We read ${site} ourselves and looked your listing up on Google Maps; nothing here is guessed, and none of it needs your Google Ads account. What it costs in money we can only tell you once you connect that, read only.`,
  };
}

export function reportFromRun(run: Run, mine: Listing | null, rivals: Listing[]): AuditSample {
  const report = run.report;
  const site = (report?.site ?? run.site).replace(/^https?:\/\//, "").replace(/\/$/, "");
  const panels: AuditPanel[] = [];
  if (mine) panels.push(listingPanel(mine, rivals));
  if (report) panels.push(websitePanel(report.findings));
  if (mine && rivals.length) panels.push(comparePanel(mine, rivals));

  const all = panels.flatMap((p) => p.lines);
  const problems = all.filter((l) => l.verdict !== "good");
  const ours = problems.filter((l) => l.who === "us");
  const good = all.length - problems.length;
  const readiness = Math.round((good / Math.max(all.length, 1)) * 100);
  const after = Math.round(((good + ours.length) / Math.max(all.length, 1)) * 100);

  const ordered = [...problems].sort(
    (a, b) =>
      Number(b.verdict === "cost") - Number(a.verdict === "cost") ||
      Number(b.who === "us") - Number(a.who === "us"),
  );

  return {
    date: `Audit, ${new Date().toLocaleDateString("en-CA", { day: "numeric", month: "long", year: "numeric" })}`,
    business: mine?.name ?? report?.business_name ?? site,
    summary:
      problems.length === 0
        ? `We checked ${site} and your Google listing, and found nothing that needs fixing first. That is rare.`
        : `${problems.length === 1 ? "One thing needs" : `${upper(say(problems.length))} things need`} doing on ${site} and your Google listing. ${ours.length > 0 ? `We do ${say(ours.length)} of them for you.` : "We send you the steps for each."}`,
    readiness,
    after,
    panels,
    ads: {
      title: "Your ads today",
      note: "Which searches you showed for this morning, what each one cost, and how many were never going to call. Google shows this to the account owner and to nobody else, so we cannot read it and neither can your competitors.",
      rows: [
        "Searches you paid for today",
        "Money spent on people who cannot buy",
        rivals.length
          ? `Where your ad sat against the ${say(rivals.length)} nearby`
          : "Where your ad sat against your competitors",
      ],
      button: "Connect Google Ads, read only",
    },
    cost: costOf(ordered, site),
    locked:
      rivals.length > 2
        ? {
            title: `How you stand against your ${say(rivals.length)} competitors`,
            note: "Rating, reviews, photos and hours, side by side, from Google Maps. Two are shown here.",
            shown: rivals.slice(0, 2).map((r) => {
              const bits = [r.name];
              bits.push(r.rating !== null ? `${r.rating} from ${r.reviews} reviews` : "no reviews");
              bits.push(`${r.photos} photos`);
              if (r.open_24h) bits.push("open 24 hours");
              return bits.join(" · ");
            }),
            total: rivals.length,
          }
        : undefined,
    bar:
      problems.length === 0
        ? "Nothing here needs fixing first. We keep watching it every morning."
        : `${ordered.length === 1 ? "One problem" : `${upper(say(ordered.length))} problems`} on your site and listing.${ours.length ? ` We fix ${say(ours.length)} of them by tomorrow morning.` : " We send you the steps today."}`,
    fixes: ordered
      .slice(0, 3)
      .map((l, i) => ({
        when: l.who === "us" || i === 0 ? "Day one" : "Week one",
        title: l.title,
        body: l.meta,
      }))
      // Day one before week one, so the plan reads in the order it happens.
      .sort((a, b) => Number(a.when === "Week one") - Number(b.when === "Week one")),
    close: {
      title:
        ours.length > 0
          ? `We can have ${ours.length === 1 ? "the first one" : "the first two"} fixed by tomorrow morning.`
          : "We can send you every step tomorrow morning.",
      body: "Then we watch it every morning, and nothing changes without your yes.",
    },
  };
}
