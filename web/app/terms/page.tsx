import type { Metadata } from "next";
import Link from "next/link";
import { LegalPage, Row, Rule, Section } from "@/components/site/legal";

export const metadata: Metadata = {
  title: "Terms at PPCWay",
  description:
    "What PPCWay does for you, what it will never do without asking, what it costs, and how either of us can walk away.",
};

const CONTACT = "support@ppcway.com";

export default function Terms() {
  return (
    <LegalPage
      title="Terms of service"
      updated="12 October 2026"
      lede="The agreement between you and PPCWay, in the plainest words we can manage. If anything here is unclear, ask us before you agree to it."
    >
      <Section title="What we do">
        <p>
          We audit your website, your Google Business Profile and, if you connect it, your Google
          Ads account, and we tell you what we find. If you go on to use the paid service, we set up
          and look after your Google Ads campaigns and explain every change in words you can check.
        </p>
      </Section>

      <Section title="What we will never do without asking">
        <Rule>
          <Row label="Change your account">
            Nothing in your Google Ads account changes unless you have approved that specific
            change. Not a category of changes agreed once: the actual change, described in plain
            words, approved before it happens.
          </Row>
          <Row label="Spend your money">
            We never raise a budget, start a campaign or change a bidding strategy on our own. Your
            spending stays where you put it until you say otherwise.
          </Row>
          <Row label="Hide what we did">
            Every automated change is written to a record before it is applied, and that record is
            yours to read whenever you like.
          </Row>
        </Rule>
      </Section>

      <Section title="What we need from you">
        <p>
          That you own the business and the website you ask us to audit, or that you are allowed to
          act for whoever does. That the Google Ads account you connect is yours to connect. And
          that what you tell us is true, because the report is only as good as what it is built on.
        </p>
      </Section>

      <Section title="What we cannot promise">
        <p>
          We cannot promise results. Advertising is an auction against other businesses, and nobody
          can guarantee a position, a price per click, or a number of enquiries. What we promise is
          the work: that the checks are real, the numbers come from Google rather than from us, and
          that we say so when we do not know something.
        </p>
        <p>
          Google can change its rules, its prices and its data at any time, and parts of this
          service depend on access Google grants us. If that access changes, we will tell you what
          it means for you.
        </p>
      </Section>

      <Section title="Money">
        <p>
          The audit is free and asks for no card. Anything beyond it is agreed with you in advance —
          what it costs, what it includes, and when it is billed — and you can stop it at the end of
          any paid period. We never spend your advertising budget: that is paid by you to Google,
          directly, on your own card.
        </p>
      </Section>

      <Section title="Walking away">
        <p>
          You can disconnect your Google Ads account at any moment, from here or from your Google
          account, without telling us. You can ask us to delete everything we hold by writing to{" "}
          <a href={`mailto:${CONTACT}`} className="text-brand font-semibold">
            {CONTACT}
          </a>
          , and we will do it within thirty days. Your campaigns stay in your own Google Ads
          account, which was always yours; nothing of yours leaves with us.
        </p>
        <p>
          We may end the service if it is used to break the law or Google&rsquo;s advertising
          policies, or if fees agreed go unpaid. We will say why.
        </p>
      </Section>

      <Section title="Responsibility">
        <p>
          We take responsibility for doing our work carefully. We are not responsible for losses we
          could not reasonably have foreseen, for decisions you make on your own account, or for
          what Google does. Where the law allows a limit, our liability is limited to what you have
          paid us in the twelve months before the problem arose. Nothing here limits liability the
          law does not allow us to limit.
        </p>
      </Section>

      <Section title="The law that applies">
        <p>
          The laws of Ontario, Canada, and the courts there. If part of this agreement turns out to
          be unenforceable, the rest of it still stands.
        </p>
        <p className="text-muted text-[15px]">
          See also our{" "}
          <Link href="/privacy" className="text-brand font-semibold">
            privacy policy
          </Link>
          .
        </p>
      </Section>
    </LegalPage>
  );
}
