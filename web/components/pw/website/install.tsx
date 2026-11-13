"use client";

import { useState } from "react";
import { CodeBox } from "@/components/pw/conversions/tag";
import { Card, Note } from "@/components/pw/create/kit";
import { Chip } from "@/components/pw/shell";
import { cn } from "@/lib/cn";
import type { SiteSetup } from "./types";

/*
  Putting the script on the merchant's website, three ways: the WordPress
  plugin, one line pasted into any site's header, or a ready-made email to
  whoever looks after the site. Above them, whether it is working: PPCWay
  knows the moment the first page on their site reports in.
*/
type Way = "wordpress" | "any" | "email";

export function Install({ setup, open }: { setup: SiteSetup; open: boolean }) {
  const [way, setWay] = useState<Way>("wordpress");
  const [shown, setShown] = useState(open);

  const mail = `mailto:?subject=${encodeURIComponent("Please add PPCWay to our website")}&body=${encodeURIComponent(
    [
      "Hello,",
      "",
      "Could you add this line to our website, just before </head>, on every page?",
      "",
      setup.snippet,
      "",
      "It is PPCWay, which looks after our Google Ads. It counts visits and leads",
      "(forms sent, phone numbers tapped) so we can see which ads bring customers.",
      "It loads after the page and does not slow it down.",
      "",
      "On WordPress there is a plugin instead: " +
        setup.script_url.replace("/t.js", "/downloads/ppcway-wordpress.zip") +
        ` (the key to paste in Settings, PPCWay is ${setup.key}).`,
      "",
      "Thank you!",
    ].join("\n"),
  )}`;

  return (
    <Card
      title={setup.installed ? "PPCWay on your website" : "Put PPCWay on your website"}
      help="One line of code. It counts visits and leads on every page, and loads after the page so it never slows it down."
      aside={
        setup.installed ? (
          <Chip tone="good">Working</Chip>
        ) : (
          <Chip tone="warn">Not installed yet</Chip>
        )
      }
    >
      <div className="flex flex-col gap-4 px-6 py-5">
        {setup.installed ? (
          <p className="text-pw-ink-600 text-[14px] leading-[20px]">
            Last heard from your website{" "}
            <span suppressHydrationWarning className="text-pw-ink font-semibold">
              {ago(setup.last_seen_at)}
            </span>
            {setup.last_seen_url ? (
              <>
                , on{" "}
                <span className="text-pw-ink font-semibold">{pageOf(setup.last_seen_url)}</span>
              </>
            ) : null}
            .
          </p>
        ) : (
          <p className="text-pw-ink-600 text-[14px] leading-[20px]">
            Once it is on your site, open any page of it. This will say{" "}
            <span className="font-semibold">Working</span> within a minute.
          </p>
        )}

        {!shown ? (
          <button
            type="button"
            onClick={() => setShown(true)}
            className="text-pw-blue hover:text-pw-blue-hover self-start text-[14px] font-semibold"
          >
            Show the install code
          </button>
        ) : (
          <>
            <div className="bg-pw-muted flex flex-wrap gap-1 self-start rounded-[12px] p-[4px]">
              {(
                [
                  ["wordpress", "WordPress"],
                  ["any", "Any other website"],
                  ["email", "Send it to your web person"],
                ] as const
              ).map(([value, label]) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => setWay(value)}
                  aria-pressed={way === value}
                  className={cn(
                    "rounded-[9px] px-3 py-[7px] text-[13px] font-semibold",
                    way === value ? "bg-pw-card text-pw-ink shadow-sm" : "text-pw-ink-500",
                  )}
                >
                  {label}
                </button>
              ))}
            </div>

            {way === "wordpress" ? (
              <ol className="text-pw-ink-700 flex list-decimal flex-col gap-3 pl-5 text-[14px] leading-[20px]">
                <li>
                  <a
                    href="/downloads/ppcway-wordpress.zip"
                    download
                    className="text-pw-blue hover:text-pw-blue-hover font-semibold"
                  >
                    Download the PPCWay plugin
                  </a>
                  .
                </li>
                <li>
                  In WordPress, go to <span className="font-semibold">Plugins</span>, then{" "}
                  <span className="font-semibold">Add New</span>,{" "}
                  <span className="font-semibold">Upload Plugin</span>, choose the file, and press{" "}
                  <span className="font-semibold">Activate</span>.
                </li>
                <li>
                  Go to <span className="font-semibold">Settings</span>, then{" "}
                  <span className="font-semibold">PPCWay</span>, and paste your key:
                  <div className="mt-2">
                    <CodeBox code={setup.key} label="Your PPCWay key" />
                  </div>
                </li>
              </ol>
            ) : null}

            {way === "any" ? (
              <div className="flex flex-col gap-3">
                <p className="text-pw-ink-700 text-[14px] leading-[20px]">
                  Paste this just before <code>&lt;/head&gt;</code>, on every page. Website builders
                  have a box for it: on Wix it is under Settings, Custom code; on Squarespace, Code
                  injection; on Shopify, the theme&rsquo;s <code>theme.liquid</code> file.
                </p>
                <CodeBox code={setup.snippet} label="PPCWay script" />
              </div>
            ) : null}

            {way === "email" ? (
              <div className="flex flex-col items-start gap-3">
                <p className="text-pw-ink-700 text-[14px] leading-[20px]">
                  An email with the code and what it is for, ready for you to send from your own
                  mail.
                </p>
                <a
                  href={mail}
                  className="bg-pw-blue hover:bg-pw-blue-hover flex h-[42px] items-center rounded-[12px] px-4 text-[15px] font-semibold text-white"
                >
                  Write the email
                </a>
              </div>
            ) : null}

            <Note>
              Forms inside a box from another company (a booking calendar, say) cannot be seen by
              any script on your site. Their own settings usually let them tell you about new
              bookings.
            </Note>
          </>
        )}
      </div>
    </Card>
  );
}

function pageOf(url: string): string {
  try {
    const u = new URL(url);
    return `${u.hostname.replace(/^www\./, "")}${u.pathname === "/" ? "" : u.pathname}`;
  } catch {
    return url;
  }
}

/** "3 minutes ago", in the merchant's own words. */
export function ago(iso: string | null): string {
  if (!iso) return "never";
  const seconds = Math.round((Date.now() - new Date(iso).getTime()) / 1000);
  const say = new Intl.RelativeTimeFormat("en", { numeric: "auto" });
  if (seconds < 60) return "just now";
  if (seconds < 3600) return say.format(-Math.round(seconds / 60), "minute");
  if (seconds < 86400) return say.format(-Math.round(seconds / 3600), "hour");
  return say.format(-Math.round(seconds / 86400), "day");
}
