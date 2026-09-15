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

/* 66:270, the plain-English Searches page. */
const alpha: Workspace = { name: "Alpha Plumbing", meta: "Mississauga, Ontario" };

export function SearchesPage() {
  return (
    <AppShell active="searches" workspace={alpha}>
      <PageHead
        title="What people actually typed to find you."
        lead="Google matches your keywords to real searches, and not always well. Here is what showed your ad in the last 30 days, and what we suggest doing with each one."
      />
      <Tiles>
        <Tile tone="brand" label="Searches that led to calls" value="23" chip="Worth keeping" />
        <Tile label="Spent on searches, no calls" value="$64" chip="Across 17 searches" />
        <Tile label="Blocked so far" value="11" chip="You approved every one" />
        <Tile label="Matched well" value="87%" progress={0.87} />
      </Tiles>
      <Columns
        aside={
          <>
            <NoticeCard
              tag="In Approvals"
              title="Block 3 searches that never call"
              body="They cost $64 in the last 30 days and brought no calls. You are on Approve-first, so nothing changes until you say yes."
              primary={{ label: "Approve all" }}
              secondary={{ label: "Review", href: "/approvals" }}
            />
            <Panel title="Blocked already">
              <Rows className="mt-1">
                <ListRow
                  title="plumbing courses mississauga"
                  meta="Blocked 8 Sep · you approved"
                  chip="Blocked"
                  dot
                />
                <ListRow
                  title="diy drain unblock"
                  meta="Blocked 8 Sep · you approved"
                  chip="Blocked"
                  dot
                />
              </Rows>
            </Panel>
          </>
        }
      >
        <Panel title="What we noticed" action={{ label: "Last 30 days", tone: "brand" }}>
          <Summary>
            Most calls come from searches with a place in them, like plumber mississauga. Searches
            with cheap or price in them get clicks and never call, so we suggest blocking them.
          </Summary>
        </Panel>
        <Panel
          title="Searches that brought calls, and one that did not"
          action={{ label: "See all 214", href: "/campaigns?view=search-terms" }}
        >
          <Rows>
            <ActivityRow
              icon="bars"
              iconTone="brand"
              title="emergency plumber mississauga"
              meta="9 calls · $18 a call · already one of your keywords"
              action="Keep"
            />
            <ActivityRow
              icon="plus"
              iconTone="brand"
              title="burst pipe repair near me"
              meta="4 calls · $21 a call · not a keyword yet"
              action="Add"
            />
            <ActivityRow
              icon="line"
              iconTone="brand"
              title="cheap plumber mississauga"
              meta="0 calls · $29 spent · waiting for your yes to block it"
            />
          </Rows>
        </Panel>
        <Panel
          title="Suggested blocks, waiting for your yes"
          action={{ label: "Approve", href: "/approvals" }}
        >
          <AdMock
            kicker="In Approvals"
            source="3 searches · $64 spent · no calls between them"
            headline="cheap plumber mississauga · plumber prices · plumbing cost estimate"
            body="People comparing prices click, read, and leave. Blocking these stops your ad showing for them. You can unblock any of them later with one click."
          />
          <Footnote>
            Search terms come from Google and can take a day to appear. Google hides some rare
            searches for privacy.
          </Footnote>
        </Panel>
      </Columns>
    </AppShell>
  );
}
