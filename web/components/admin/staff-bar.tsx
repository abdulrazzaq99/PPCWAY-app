import type { Whoami } from "@/lib/admin";
import { SignOut } from "./sign-out";

/*
  The one piece of chrome this panel adds to the app's own vocabulary, and the
  one place it raises its voice.

  The worst failure an internal panel has is not a wrong number. It is a member
  of staff who has forgotten they are looking at somebody else's business --
  reading Alpha Plumbing's figures while answering a question about Beacon
  Roofing, or worse, acting on them. Every other screen in PPCWay belongs to
  the person reading it. These do not.

  So the bar is always there, it names the level in force, and when a named
  business is open it says whose. It is not a decoration and it is not
  dismissible: a banner somebody can close is a banner that is closed.

  It uses the app's own tokens -- ink, border, the same radii -- and takes its
  weight from the one colour the merchant app never uses for chrome. That is
  the whole of the design decision: same materials, one deliberate exception,
  spent on the thing that matters.
*/

const WHAT: Record<string, string> = {
  support: "You can read figures. You cannot change anything.",
  engineer: "You can read the platform and re-run jobs. You cannot write to Google Ads.",
  principal: "You can stop writes and grant access.",
};

export function StaffBar({
  who,
  looking_at,
}: {
  who: Whoami;
  /* The business currently open, where one is. */
  looking_at?: string;
}) {
  if (!who.staff) return null;
  return (
    <div
      className="border-pw-ink text-pw-night-text bg-pw-night sticky top-0 z-40 border-b"
      role="region"
      aria-label="Internal access"
    >
      <div className="mx-auto flex max-w-[1200px] flex-wrap items-center gap-x-3 gap-y-1 px-4 py-2 text-[13px] leading-[18px]">
        <span className="text-pw-night-text font-semibold">PPCWay internal</span>
        <span className="text-pw-night-border-strong" aria-hidden>
          |
        </span>
        <span className="text-pw-night-muted">
          {who.level} access. {WHAT[who.level] ?? ""}
        </span>
        {looking_at ? (
          <>
            <span className="text-pw-night-border-strong" aria-hidden>
              |
            </span>
            {/*
              The sentence that does the work. Not "Viewing: Alpha Plumbing" --
              a label and a value read as a field, and a field reads as part of
              the furniture. A sentence about somebody else's business does not.
            */}
            <span className="text-pw-night-text font-semibold">
              You are looking at {looking_at}&rsquo;s account, not your own.
            </span>
          </>
        ) : null}
        <span className="ml-auto flex items-center gap-3">
          <span className="text-pw-night-muted">
            {who.who ? who.who : "signed in"} &middot; every account you open is recorded
          </span>
          {/*
            Two ways out, because they are different things and conflating them
            is what made somebody ask where the sign-out was. "Leave the panel"
            goes to your own dashboard and you stay signed in; "Sign out" ends
            the session. The shell these screens are built from has no account
            menu at all, so without this there was no sign-out anywhere on an
            internal screen.
          */}
          <a
            href="/home"
            className="text-pw-night-text underline underline-offset-2 hover:no-underline"
          >
            Leave the panel
          </a>
          <span className="text-pw-night-border-strong" aria-hidden>
            |
          </span>
          <SignOut />
        </span>
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
    <div className="mx-auto max-w-[680px] px-4 py-20">
      <h1 className="text-pw-ink text-[22px] leading-[28px] font-semibold">
        This part of PPCWay is for our own staff
      </h1>
      <p className="text-pw-ink-700 mt-3 text-[15px] leading-[22px]">
        {trouble ||
          "There is nothing here for you to do. Your own dashboard has everything about your account."}
      </p>
      <a
        href="/dashboard"
        className="text-pw-blue mt-5 inline-block text-[15px] leading-[22px] font-medium underline underline-offset-2"
      >
        Go to your dashboard
      </a>
    </div>
  );
}
