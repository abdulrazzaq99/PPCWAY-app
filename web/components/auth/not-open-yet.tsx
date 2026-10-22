import { AuthShell } from "@/components/auth/auth-shell";
import { LinkButton, TextLink } from "@/components/ui/button";

/*
  The door, while PPCWay is open to some people and not to everybody.

  It does not apologise and it does not collect an address for a list nobody
  reads. It sends people to the thing that is genuinely ready — the free audit,
  which asks for no account and will email them the report — because that is
  both the honest answer and the one worth their minute.
*/
export function NotOpenYet() {
  return (
    <AuthShell
      headline="The free audit is ready. The rest is not, yet."
      body="We are letting businesses in a few at a time, so that everybody who arrives gets a service that works. The audit below is the finished part, and it needs no account."
      footnote="No sign-up, nothing changed on your website."
      below={
        <>
          Already have an account? <TextLink href="/login">Sign in</TextLink>
        </>
      }
    >
      <div className="flex flex-col gap-5">
        <div>
          <h1 className="text-[24px] leading-[30px] font-semibold">Accounts open soon</h1>
          <p className="text-muted mt-3 text-[15px] leading-[23px]">
            What you can do now, free and without an account:
          </p>
        </div>

        <ul className="text-muted flex flex-col gap-3 text-[15px] leading-[22px]">
          <li>
            <strong className="text-ink">Check your website and your Google listing.</strong> A
            score out of 100, every check explained, and the ones costing you money first.
          </li>
          <li>
            <strong className="text-ink">See how you compare</strong> with the businesses you
            compete with on Google Maps.
          </li>
          <li>
            <strong className="text-ink">Have the report emailed to you</strong> as a PDF, to keep
            or to send to whoever looks after your website.
          </li>
        </ul>

        <LinkButton href="/audit" full>
          Run my free audit
        </LinkButton>
      </div>
    </AuthShell>
  );
}
