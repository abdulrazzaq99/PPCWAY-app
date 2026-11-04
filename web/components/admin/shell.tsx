import {
  ArrowsClockwiseIcon,
  EyeIcon,
  GaugeIcon,
  KeyIcon,
  LockSimpleIcon,
  LockSimpleOpenIcon,
  SlidersHorizontalIcon,
  SquaresFourIcon,
  StorefrontIcon,
  WarningIcon,
} from "@phosphor-icons/react/dist/ssr";
import type { Icon } from "@phosphor-icons/react";
import Image from "next/image";
import Link from "next/link";
import type { ReactNode } from "react";
import { LEVEL_WORDS, count, type Door, type Whoami } from "@/lib/admin";
import { adMono, adSans } from "./fonts";
import { PhoneMenu } from "./menu";
import { Search } from "./search";
import { SignOut } from "./sign-out";
import { Mark } from "./ui";

/*
  The console's frame: the "ruled T-frame" from the study's dark screens. A
  labelled sidebar and a 64px top bar on one ground, divided only by 1px
  rules, with the work on the same ground beside them. No inset sheet, no
  tinted chrome; depth is the panels' one step darker than the ground.

  A labelled sidebar rather than the icon rail the style was dealt: the rail
  suits five destinations or fewer, and this console has seven, used by staff
  who should not have to learn what an icon means before they can find a
  failing sync.

  The active destination is the style's one mark: its label brightens, and a
  1px line in the accent lights the stretch of the sidebar's own edge beside
  it. Nothing is filled.

  The top bar carries three real things: the way back from wherever you are,
  the search every screen needs, and the door, which is whether PPCWay may
  write to Google at all. That last one is on every screen because it is the
  most consequential state in the product, and somebody looking at a
  merchant's proposals should never have to go and find out whether they
  could be sent.
*/

type Item = { href: string; label: string; icon: Icon; needs: string; count?: number };

function groups(failures?: number): { title?: string; items: Item[] }[] {
  return [
    {
      items: [
        {
          href: "/admin/metrics",
          label: "Overview",
          icon: SquaresFourIcon,
          needs: "read_platform",
        },
        { href: "/admin", label: "Merchants", icon: StorefrontIcon, needs: "read_merchant" },
      ],
    },
    {
      title: "Running",
      items: [
        { href: "/admin/jobs", label: "Jobs", icon: ArrowsClockwiseIcon, needs: "run_job" },
        /*
          The one count in the sidebar, because it is the one queue that needs
          a person, and "Failures 3" says what three is.
        */
        {
          href: "/admin/errors",
          label: "Failures",
          icon: WarningIcon,
          needs: "read_errors",
          count: failures,
        },
        { href: "/admin/quota", label: "Quota", icon: GaugeIcon, needs: "read_platform" },
      ],
    },
    {
      title: "Control",
      items: [
        {
          href: "/admin/platform",
          label: "Settings",
          icon: SlidersHorizontalIcon,
          needs: "read_platform",
        },
        { href: "/admin/staff", label: "Access", icon: KeyIcon, needs: "grant_staff" },
      ],
    },
  ];
}

function Nav({ who, here, failures }: { who: Whoami; here: string; failures?: number }) {
  return (
    <nav aria-label="Internal console">
      {groups(failures).map((group, at) => {
        const shown = group.items.filter((one) => who.may.includes(one.needs));
        if (!shown.length) return null;
        return (
          <div key={group.title ?? at} className={at ? "mt-6" : ""}>
            {group.title ? (
              <p className="text-ad-faint px-5 pb-1.5 text-[12px] leading-[18px]">{group.title}</p>
            ) : null}
            <ul>
              {shown.map((one) => {
                const current = here === one.href;
                const Glyph = one.icon;
                return (
                  <li key={one.href}>
                    <Link
                      href={one.href}
                      aria-current={current ? "page" : undefined}
                      className={[
                        "relative flex h-9 items-center gap-3 px-5 text-[13px] transition-colors duration-150",
                        current ? "text-ad-text font-medium" : "text-ad-muted hover:text-ad-text",
                      ].join(" ")}
                    >
                      <Glyph
                        size={16}
                        aria-hidden
                        className={current ? "text-ad-accent" : "text-ad-faint"}
                      />
                      <span className="min-w-0 flex-1 truncate">{one.label}</span>
                      {one.count ? (
                        <span className="ad-num text-ad-negative text-[12px]">
                          {count(one.count)}
                        </span>
                      ) : null}
                      {current ? (
                        <span
                          aria-hidden
                          className="bg-ad-accent absolute top-1.5 -right-px bottom-1.5 w-px max-lg:hidden"
                        />
                      ) : null}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        );
      })}
    </nav>
  );
}

function Brand() {
  return (
    <Link href="/admin" className="flex items-center gap-3" aria-label="PPCWay internal console">
      <Image
        src="/brand/ppcway-logo-white.svg"
        alt="PPCway"
        width={104}
        height={24}
        priority
        className="h-6 w-auto"
      />
      <span className="border-ad-control text-ad-muted border-l pl-3 text-[12px] leading-[16px]">
        Internal
      </span>
    </Link>
  );
}

function Me({ who }: { who: Whoami }) {
  const name = who.who ?? "Signed in";
  return (
    <div className="border-ad-border flex items-center gap-2 border-t py-4 pr-3 pl-5">
      <Mark seed={name} name={name} size={26} />
      <div className="min-w-0 flex-1">
        {/* A long address truncates, and says itself in full on hover. */}
        <p className="truncate text-[13px] leading-[18px]" title={name}>
          {name}
        </p>
        <p className="text-ad-faint text-[12px] leading-[16px]">
          {LEVEL_WORDS[who.level] ?? who.level} access
        </p>
      </div>
      <SignOut />
    </div>
  );
}

const DOOR: Record<Door["state"], { words: string; short: string; tone: string }> = {
  on: {
    words: "Google writes on",
    short: "Writes on",
    tone: "bg-ad-positive-tint text-ad-positive-ink",
  },
  off: {
    words: "Google writes off",
    short: "Writes off",
    tone: "bg-ad-warning-tint text-ad-warning",
  },
  stopped: {
    words: "Google writes stopped",
    short: "Stopped",
    tone: "bg-ad-negative-tint text-ad-negative",
  },
};

/* The door, on every screen. It links to the switch. */
function DoorChip({ door }: { door: Door }) {
  const look = DOOR[door.state];
  const Glyph = door.state === "on" ? LockSimpleOpenIcon : LockSimpleIcon;
  return (
    <Link
      href="/admin/platform"
      title={door.words}
      className={`inline-flex h-[30px] flex-none items-center gap-2 rounded-full px-3 text-[12px] font-medium whitespace-nowrap transition-opacity hover:opacity-85 ${look.tone}`}
    >
      <Glyph size={14} aria-hidden />
      <span className="hidden sm:inline">{look.words}</span>
      <span className="sm:hidden">{look.short}</span>
    </Link>
  );
}

export type Crumb = { label: string; href?: string };

export function Shell({
  who,
  here,
  door,
  crumbs,
  lookingAt,
  failures,
  lookedFor = "",
  children,
}: {
  who: Whoami;
  /* Which destination this screen belongs to. */
  here: string;
  door?: Door;
  crumbs?: Crumb[];
  /* Set on a merchant's own screen: the name of the business being looked at. */
  lookingAt?: string;
  failures?: number;
  lookedFor?: string;
  children: ReactNode;
}) {
  return (
    <div
      className={`${adSans.variable} ${adMono.variable} adm min-h-[100dvh] lg:grid lg:grid-cols-[232px_minmax(0,1fr)]`}
    >
      <aside className="border-ad-border sticky top-0 hidden h-[100dvh] flex-col border-r lg:flex">
        <div className="border-ad-border flex h-16 flex-none items-center border-b px-5">
          <Brand />
        </div>
        <div className="flex-1 py-5">
          <Nav who={who} here={here} failures={failures} />
        </div>
        <Me who={who} />
      </aside>

      <div className="flex min-w-0 flex-col">
        <header className="border-ad-border bg-ad-ground sticky top-0 z-30 flex h-14 flex-none items-center gap-3 border-b px-4 sm:px-6 lg:h-16 lg:gap-5 lg:px-8">
          <PhoneMenu>
            <div className="px-5 pt-5 pb-3">
              <Brand />
            </div>
            <div className="px-5 pb-5">
              <Search id="ad-find-phone" defaultValue={lookedFor} wide />
            </div>
            <div className="flex-1 pb-6">
              <Nav who={who} here={here} failures={failures} />
            </div>
            <Me who={who} />
          </PhoneMenu>

          <div className="lg:hidden">
            <Image
              src="/brand/ppcway-icon.svg"
              alt="PPCway internal"
              width={24}
              height={24}
              className="h-6 w-6"
            />
          </div>

          {crumbs?.length ? (
            <nav aria-label="Where you are" className="hidden min-w-0 md:block">
              <ol className="flex min-w-0 items-center gap-2 text-[13px]">
                {crumbs.map((one, at) => (
                  <li key={one.label} className="flex min-w-0 items-center gap-2">
                    {at ? <span className="text-ad-control">/</span> : null}
                    {one.href ? (
                      <Link
                        href={one.href}
                        className="text-ad-muted hover:text-ad-text whitespace-nowrap transition-colors"
                      >
                        {one.label}
                      </Link>
                    ) : (
                      <span className="text-ad-text truncate font-medium" aria-current="page">
                        {one.label}
                      </span>
                    )}
                  </li>
                ))}
              </ol>
            </nav>
          ) : null}

          <div className="hidden md:block">
            <Search id="ad-find" defaultValue={lookedFor} shortcut />
          </div>

          <div className="ml-auto flex min-w-0 items-center gap-3">
            {lookingAt ? (
              /*
                The sentence that does the work. Not "Viewing: Alpha Plumbing",
                which reads as a field; a sentence about somebody else's
                business does not.
              */
              <p className="bg-ad-warning-tint text-ad-warning hidden h-[30px] min-w-0 items-center gap-2 truncate rounded-full px-3 text-[12px] font-medium md:inline-flex">
                <EyeIcon size={14} aria-hidden className="flex-none" />
                <span className="truncate">You are in {lookingAt}&rsquo;s account</span>
              </p>
            ) : (
              <p className="text-ad-faint hidden items-center gap-2 text-[12px] xl:flex">
                <EyeIcon size={14} aria-hidden />
                Opening an account is recorded
              </p>
            )}
            {door ? <DoorChip door={door} /> : null}
          </div>
        </header>

        {lookingAt ? (
          <p className="bg-ad-warning-tint text-ad-warning flex items-center gap-2 px-4 py-2 text-[12px] font-medium md:hidden">
            <EyeIcon size={14} aria-hidden className="flex-none" />
            You are in {lookingAt}&rsquo;s account
          </p>
        ) : null}

        <main className="min-w-0 flex-1 px-4 pt-6 pb-12 sm:px-6 lg:px-8 lg:pt-8">{children}</main>
      </div>
    </div>
  );
}
