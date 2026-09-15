import { AppShell, type Workspace } from "./shell";
import {
  ActivityRow,
  AdMock,
  Columns,
  Footnote,
  ListRow,
  NoticeCard,
  PageHead,
  Panel,
  Rows,
  Summary,
  Tile,
  Tiles,
} from "./blocks";

/* 67:946, the Help page. */
const alpha: Workspace = { name: "Alpha Plumbing", meta: "Mississauga, Ontario" };

export function HelpPage() {
  return (
    <AppShell active="help" workspace={alpha}>
      <PageHead
        title="How can we help?"
        lead="Answers to the questions people ask most, in plain words. If you would rather talk to a person, we reply within one working day."
      />
      <Tiles>
        <Tile tone="brand" label="Talk to a person" value="1 day" chip="Usual reply time" />
        <Tile label="Your account" value="Healthy" chip="Nothing needs fixing" />
        <Tile label="Open requests" value="0" chip="None waiting on us" />
        <Tile label="PPCWay status" value="All working" progress={1} />
      </Tiles>
      <Columns
        aside={
          <>
            <NoticeCard
              tone="brand"
              tag="Free on Growth"
              title="Book a 20 minute call"
              body="Walk through your first month with someone who knows Google Ads well. Bring your questions, and we will bring your numbers."
              primary={{ label: "Pick a time" }}
              secondary={{ label: "Later" }}
            />
            <Panel title="Short guides">
              <Rows className="mt-1">
                <ListRow
                  title="Your first week"
                  meta="What to expect before the first calls"
                  chip="5 min"
                  dot
                />
                <ListRow
                  title="Approve-first, explained"
                  meta="What we ask about, and why"
                  chip="3 min"
                  dot
                />
              </Rows>
            </Panel>
          </>
        }
      >
        <Panel title="Popular this week" action={{ label: "Search all help", tone: "brand" }}>
          <Summary>
            Why did my cost per call go up? What happens if my card is declined at Google? Can I
            pause for a holiday? Why doesn&rsquo;t Google&rsquo;s call count match my phone?
          </Summary>
        </Panel>
        <Panel title="Common questions" action={{ label: "See all" }}>
          <Rows>
            <ActivityRow
              icon="bars"
              iconTone="brand"
              title="Why did PPCWay change my bid?"
              meta="Every change has its reason in Activity. Here is how to read one."
              action="Read"
            />
            <ActivityRow
              icon="plus"
              iconTone="brand"
              title="Why don't Google's numbers match my phone?"
              meta="Consent banners and Google's own counting rules, explained."
              action="Read"
            />
            <ActivityRow
              icon="line"
              iconTone="brand"
              title="How do I pause for a holiday?"
              meta="One click, and what happens when you switch back on."
            />
          </Rows>
        </Panel>
        <Panel title="Talk to a person" action={{ label: "Email us" }}>
          <AdMock
            kicker="Support"
            source="help@ppcway.com · Monday to Friday, 9 to 5 Eastern"
            headline="A real person reads every message"
            body="Tell us what you expected and what happened instead. With your permission we can look at your account, and we never change anything while we look."
          />
          <Footnote>
            Whenever support opens your account, you get an email saying who and when.
          </Footnote>
        </Panel>
      </Columns>
    </AppShell>
  );
}
