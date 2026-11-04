import type { Whoami } from "@/lib/admin";
import { SignOut } from "./sign-out";

/*
  The one piece of chrome this panel adds, and the one place it raises its
  voice.

  The worst failure an internal panel has is not a wrong number. It is a member
  of staff who has forgotten they are looking at somebody else's business.
  Every other screen in PPCWay belongs to the person reading it. These do not.

  It is not dismissible, because a banner somebody can close is a banner that
  is closed.

  Rewritten for density and for phones. The first version strung five things
  across one line with middle dots between them, which is the separator you
  reach for when you have not decided what is important. On a handset it
  wrapped into four ragged lines. Now it is two rows that stack honestly: who
  you are and what you may do, then where you are and the way out.
*/

const WHAT: Record<string, string> = {
  support: "Read only.",
  engineer: "Read the platform, re-run jobs.",
  principal: "Stop writes, grant access.",
};

export function StaffBar({ who, looking_at }: { who: Whoami; looking_at?: string }) {
  if (!who.staff) return null;
  return (
    <div
      className="bg-pw-night text-pw-night-text sticky top-0 z-40"
      role="region"
      aria-label="Internal access"
    >
      <div className="mx-auto flex max-w-[1200px] flex-col gap-1 px-4 py-2 sm:flex-row sm:items-center sm:gap-4 sm:px-6">
        <p className="flex min-w-0 items-center gap-2 text-[13px] leading-[18px]">
          {/*
            The product's mark. A screen with no name on it could belong to
            anybody, and an internal panel is exactly where somebody needs to
            know which product they are about to change. Drawn from the brand
            blue on the night ground rather than a black square with a letter.
          */}
          <span
            aria-hidden
            className="bg-pw-blue flex h-5 w-5 shrink-0 items-center justify-center rounded-[6px] text-[11px] leading-none font-bold text-white"
          >
            P
          </span>
          <span className="font-semibold whitespace-nowrap">PPCWay internal</span>
          <span className="text-pw-night-muted truncate">
            {who.level} access. {WHAT[who.level] ?? ""}
          </span>
        </p>

        {looking_at ? (
          /*
            The sentence that does the work. Not "Viewing: Alpha Plumbing" -- a
            label and a value read as a field, and a field reads as part of the
            furniture. A sentence about somebody else's business does not.
          */
          <p className="text-pw-warn-bg text-[13px] leading-[18px] font-semibold sm:ml-auto">
            You are in {looking_at}&rsquo;s account, not your own.
          </p>
        ) : null}

        <p
          className={`text-pw-night-muted flex items-center gap-4 text-[13px] leading-[18px] ${
            looking_at ? "" : "sm:ml-auto"
          }`}
        >
          <a href="/home" className="hover:text-pw-night-text underline underline-offset-2">
            Your dashboard
          </a>
          <SignOut />
        </p>
      </div>
    </div>
  );
}

/*
  What somebody who is not staff sees at /admin. A plain sentence, not a 403
  screen: the likeliest reader is a merchant who followed a link, and telling
  them the page does not exist would be a lie while telling them they are
  forbidden sounds like an accusation.
*/
export function NotForYou({ trouble }: { trouble?: string }) {
  return (
    <main className="mx-auto max-w-[560px] px-4 py-24">
      <h1 className="text-pw-ink text-[22px] leading-[28px] font-semibold">
        This part of PPCWay is for our own staff
      </h1>
      <p className="text-pw-ink-700 mt-3 text-[15px] leading-[22px]">
        {trouble ||
          "There is nothing here for you to do. Your own dashboard has everything about your account."}
      </p>
      <a
        href="/home"
        className="text-pw-blue mt-5 inline-block text-[15px] leading-[22px] font-medium underline underline-offset-2"
      >
        Go to your dashboard
      </a>
    </main>
  );
}
