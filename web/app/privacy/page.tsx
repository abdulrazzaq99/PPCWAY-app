import type { Metadata } from "next";
import Link from "next/link";
import { LegalPage, Row, Rule, Section } from "@/components/site/legal";

export const metadata: Metadata = {
  title: "Privacy at PPCWay",
  description:
    "What PPCWay collects, what it does with your Google Ads data, who else sees it, and how to get rid of it.",
};

/*
  Written to be true of the code as it stands, not of a product we might build.
  Google's reviewer reads this page to decide whether the adwords permission is
  honestly described, so anything we start doing has to arrive here first.
*/
const CONTACT = "abdulrazzaq.devv@gmail.com";

export default function Privacy() {
  return (
    <LegalPage
      title="Privacy"
      updated="12 October 2026"
      lede="PPCWay reads your Google Ads account to tell you what is wrong with it. This page says exactly what we look at, what we keep, who else sees it, and how to make us forget it."
    >
      <Section title="Who we are">
        <p>
          PPCWay is operated from Mississauga, Ontario, Canada. We run Google Ads for small
          businesses, and we run a free audit that anyone can use without an account. For anything
          on this page, write to{" "}
          <a href={`mailto:${CONTACT}`} className="text-brand font-semibold">
            {CONTACT}
          </a>
          .
        </p>
      </Section>

      <Section title="What we collect, and why">
        <Rule>
          <Row label="The free audit">
            Your business name, your website address and the town you gave. If you asked us to send
            the report, your name, email and phone. We read your website&rsquo;s public pages, and
            we read your Google Business Profile and those of nearby businesses in the same trade.
          </Row>
          <Row label="Your account">
            If you sign in with Google, we receive your name, your email address and the account
            identifier Google gives us. We never see your Google password.
          </Row>
          <Row label="Your Google Ads account">
            Only if you connect one, and only what the audit needs: what your campaigns spent, the
            searches your ads appeared for, your keywords and the Quality Score Google gives them,
            how much of the auction your budget missed, and whether any of your ads have been
            disapproved.
          </Row>
          <Row label="Ordinary technical records">
            Server logs of requests, kept briefly, so faults can be found. We do not advertise to
            you and we do not track you around the internet.
          </Row>
        </Rule>
      </Section>

      <Section title="What we do with your Google Ads data">
        <p>
          We read it. We do not change anything in your account without asking you about that
          specific change first, and every automated change is written to a record you can read
          before it is applied.
        </p>
        <p>
          We use it for one thing: producing and improving the report we show you, and the work you
          have asked us to do on your account. We do not sell it. We do not pool it with other
          businesses&rsquo; data to sell insights. We do not use it to train artificial intelligence
          models, our own or anyone else&rsquo;s.
        </p>
        <p className="border-line-soft bg-panel-alt rounded-[14px] border p-4 text-[15px] leading-[24px]">
          <strong>Limited Use.</strong> PPCWay&rsquo;s use and transfer of information received from
          Google APIs adheres to the{" "}
          <a
            href="https://developers.google.com/terms/api-services-user-data-policy"
            className="text-brand font-semibold"
            rel="noreferrer"
            target="_blank"
          >
            Google API Services User Data Policy
          </a>
          , including the Limited Use requirements.
        </p>
      </Section>

      <Section title="Who else sees it">
        <Rule>
          <Row label="Google">
            Because it is your Google Ads account, your Google Business Profile and Google&rsquo;s
            own speed test. Connecting is done through Google&rsquo;s sign-in, so Google knows you
            granted us access, and you can withdraw it from your Google account at any time.
          </Row>
          <Row label="Anthropic">
            Our artificial intelligence provider. When the report is written, parts of your
            website&rsquo;s wording may be sent to Anthropic to put the findings into plain English.
            Anthropic does not use it to train models.
          </Row>
          <Row label="Our hosting">
            The service runs on Google Cloud in Toronto, and the database is operated by Neon. They
            hold the data on our behalf and do nothing else with it.
          </Row>
          <Row label="Nobody else">
            We do not sell or rent anything to anyone. If we are ever legally compelled to hand
            something over, we will tell you unless we are forbidden from doing so.
          </Row>
        </Rule>
      </Section>

      <Section title="How it is kept">
        <p>
          The permission that lets us read your Google Ads account is encrypted before it is stored,
          and it is never written to a log or shown on a screen. Only one service in our system
          holds the keys to Google, and nothing else can reach your account.
        </p>
        <p>
          Audits are kept while your account exists, so you can compare one month against the next.
          The free audit you run without an account is kept for ninety days, which is long enough
          for you to come back and claim it.
        </p>
      </Section>

      <Section title="How to make us stop">
        <Rule>
          <Row label="Disconnect Google Ads">
            From your settings here, or from your{" "}
            <a
              href="https://myaccount.google.com/permissions"
              className="text-brand font-semibold"
              rel="noreferrer"
              target="_blank"
            >
              Google account
            </a>
            , without asking us. Access stops immediately and we delete the stored permission.
          </Row>
          <Row label="Delete your account">
            Write to{" "}
            <a href={`mailto:${CONTACT}`} className="text-brand font-semibold">
              {CONTACT}
            </a>{" "}
            and we remove your account, your audits and anything we hold from your Google Ads
            account within thirty days.
          </Row>
          <Row label="Ask what we hold">
            Under Canadian privacy law you may ask for a copy of what we hold about you, ask us to
            correct it, or complain to the Office of the Privacy Commissioner of Canada. Write to us
            first and we will answer within thirty days.
          </Row>
        </Rule>
      </Section>

      <Section title="Changes to this page">
        <p>
          If we start doing something new with your data, this page changes before we start, not
          after. The date at the top says when it last did.
        </p>
        <p className="text-muted text-[15px]">
          See also our{" "}
          <Link href="/terms" className="text-brand font-semibold">
            terms of service
          </Link>
          .
        </p>
      </Section>
    </LegalPage>
  );
}
