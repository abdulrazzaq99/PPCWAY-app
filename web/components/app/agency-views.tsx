import { AppShell, type Workspace } from "./shell";
import {
  ActivityRow,
  AdMock,
  Choice,
  Columns,
  FieldRow,
  Footnote,
  ListRow,
  NoticeCard,
  PageHead,
  Panel,
  PanelText,
  Rows,
  Summary,
  Tile,
  Tiles,
  Toggle,
} from "./blocks";
import type { AgencyView } from "./view-names";

/*
  Brightpath Media, the agency: the console across six clients, adding a client,
  and the white-label settings.
*/
const brightpath: Workspace = { name: "Brightpath Media", meta: "Agency · 6 clients" };

export function AgencyPage({ view }: { view: AgencyView }) {
  if (view === "add-client") return <AddClient />;
  if (view === "brand") return <Brand />;
  return <AgencyOverview />;
}

/* ---------- 67:777 ---------- */
function AgencyOverview() {
  return (
    <AppShell
      kind="agency"
      active="overview"
      workspace={brightpath}
      initials="PS"
      badges={{ approvals: 4 }}
    >
      <PageHead
        title="Six clients, two need you today."
        lead="Every account you manage, in one place. Open any client to see it exactly as they do. Approvals stay with each client's owner and team."
      />
      <Tiles>
        <Tile tone="brand" label="Calls this week" value="212" chip="Across all 6 clients" />
        <Tile label="Spent this week" value="$4,380" chip="Of $5,600 budgeted" />
        <Tile label="Waiting on approval" value="4" chip="At 2 clients" />
        <Tile label="Healthy accounts" value="4 of 6" progress={150 / 226} />
      </Tiles>
      <Columns
        aside={
          <>
            <NoticeCard
              tone="red"
              tag="Critical"
              title="Hillside Dental's card was declined"
              body="Google will stop their ads in about 2 days. Only they can update the card, on Google's own billing page. We have emailed them the link."
              primary={{ label: "Send a reminder" }}
              primaryTone="red"
              secondary={{ label: "Open account" }}
            />
            <Panel title="Waiting on approval">
              <Rows className="mt-1">
                <ListRow
                  title="Alpha Plumbing"
                  meta="A budget change and 3 searches to block"
                  chip="2"
                  chipTone="amber"
                  dot
                />
                <ListRow
                  title="Northgate HVAC"
                  meta="Lower 2 bids that cost too much"
                  chip="2"
                  chipTone="amber"
                  dot
                />
              </Rows>
            </Panel>
          </>
        }
      >
        <Panel
          title="This week in one sentence"
          action={{ label: "Send to clients", tone: "brand" }}
        >
          <Summary>
            Calls are up at three clients, flat at two and down at Northgate HVAC. Hillside Dental
            needs a new card at Google before its ads stop, and Alpha Plumbing has two changes
            waiting for approval.
          </Summary>
        </Panel>
        <Panel title="Clients" action={{ label: "Add a client", href: "/agency/clients/new" }}>
          <Rows>
            <ActivityRow
              icon="bars"
              iconTone="brand"
              title="Alpha Plumbing · Mississauga"
              meta="58 calls in 30 days · $21 a call · 2 waiting"
              action="Open"
              href="/overview?view=agency-view"
            />
            <ActivityRow
              icon="bar"
              iconTone="red"
              title="Hillside Dental · Oakville"
              meta="Card declined at Google · ads stop in about 2 days"
              metaTone="red"
              action="Open"
              href="/overview?view=card-declined"
            />
            <ActivityRow
              icon="line"
              iconTone="brand"
              title="Northgate HVAC · Brampton"
              meta="61 calls in 30 days · $19 a call · 2 waiting"
              href="/overview?view=northgate"
            />
          </Rows>
        </Panel>
        <Panel title="Reports for your clients" action={{ label: "Choose clients" }}>
          <AdMock
            kicker="Monthly, under your name"
            source="Sent from reports@brightpath.ca with your logo"
            headline="One PDF per client, or one for all six"
            body="Each client's report uses only their own numbers and their own plain-English summary. No client can ever see another client's data."
          />
          <Footnote>
            Give any client their own login to see their account and nothing else.
          </Footnote>
        </Panel>
      </Columns>
    </AppShell>
  );
}

/* ---------- 87:8744 ---------- */
function AddClient() {
  return (
    <AppShell
      kind="agency"
      active="overview"
      workspace={brightpath}
      initials="PS"
      badges={{ approvals: 4 }}
    >
      <PageHead
        title="Add a client."
        lead="Your client connects their own Google Ads account and agrees what Brightpath can do. Budgets, billing and the Google connection always stay with them."
      />
      <Tiles>
        <Tile tone="brand" label="Clients" value="6 of 10" chip="On the Agency plan" />
        <Tile label="Invites waiting" value="0" chip="This is the first" />
        <Tile label="Clients you can view" value="6" chip="Agency access is view only" />
        <Tile label="Plan used" value="60%" progress={0.6} />
      </Tiles>
      <Columns
        aside={
          <>
            <NoticeCard
              tone="amber"
              compact
              title="What the owner gets"
              body="An email from Brightpath asking them to connect Google Ads and confirm what you can do. They can change it, or remove you, at any time."
              primary={{ label: "Send the invite" }}
            />
            <Panel title="If a client leaves" tone="plain">
              <PanelText>
                Your access ends straight away. Their campaigns, history and reports stay with them.
              </PanelText>
            </Panel>
          </>
        }
      >
        <Panel title="Invite the business owner" tone="plain">
          <FieldRow label="Business name" value="Lakeside Painting" />
          <FieldRow label="Owner's email" value="tom@lakesidepainting.ca" type="email" />
        </Panel>
        <Panel title="What Brightpath can do" tone="plain">
          <Choice
            name="access"
            selected
            title="See everything, change nothing"
            meta="Dashboards, reports, activity and alerts, across all your clients in one place."
            chip="Agency access"
          />
          <Choice
            name="access"
            disabled
            title="Approve changes"
            meta="Only the owner and their own team approve. If the owner wants you to, they add you to their team as a team member."
            chip="Owner decides"
            chipTone="grey"
          />
        </Panel>
        <Panel title="Who at Brightpath can see it" tone="plain">
          <Rows className="mt-1">
            <ListRow
              title="Priya Shah"
              meta="Account manager"
              right={<Toggle on label="Priya Shah" />}
            />
            <ListRow
              title="Ben Ortiz"
              meta="Designer"
              right={<Toggle on={false} label="Ben Ortiz" />}
            />
          </Rows>
        </Panel>
      </Columns>
    </AppShell>
  );
}

/* ---------- 81:3137 ---------- */
function Brand() {
  const swatches = ["#2f5bd3", "#0f766e", "#7c3aed", "#c2410c"];
  return (
    <AppShell
      kind="agency"
      active="settings"
      workspace={brightpath}
      initials="PS"
      badges={{ approvals: 4 }}
    >
      <PageHead
        title="Your brand on every client screen."
        lead="Clients sign in at your address, see your logo and colour, and get reports from your email. Google still sees PPCWay as the tool running the ads, so nothing changes on Google's side."
      />
      <Tiles>
        <Tile tone="brand" label="Custom domain" value="Checking" chip="app.brightpath.ca" />
        <Tile label="Logo and colour" value="Set" chip="Shown on 6 client logins" />
        <Tile label="Reports sent from" value="Your email" chip="reports@brightpath.ca" />
        <Tile label="Clients on your brand" value="6 of 6" progress={1} />
      </Tiles>
      <Columns
        aside={
          <>
            <Panel title="What clients see" tone="plain">
              <div className="border-line mt-[14px] rounded-[14px] border bg-[#f7f9fb] px-6 py-6">
                <p className="flex items-center gap-2">
                  <span className="bg-brand inline-block size-5 rounded-[6px]" />
                  <span className="text-ink text-[15px] font-bold">brightpath</span>
                </p>
                <p className="text-ink mt-3 text-[17px] leading-[21px] font-semibold">
                  Sign in to see your ads
                </p>
                <div className="border-line mt-3 h-[38px] rounded-[10px] border bg-white" />
                <div className="border-line mt-3 h-[38px] rounded-[10px] border bg-white" />
                <div className="bg-brand mt-3 flex h-10 items-center justify-center rounded-full text-[14px] font-semibold text-white">
                  Sign in
                </div>
              </div>
              <Rows className="mt-2">
                <ListRow
                  title={<>Show &ldquo;Powered by PPCWay&rdquo;</>}
                  meta="Off on your plan"
                  right={<Toggle on={false} label="Show Powered by PPCWay" />}
                />
              </Rows>
            </Panel>
            <Panel title="What stays PPCWay" tone="plain">
              <Rows className="mt-1">
                <ListRow
                  title="Access to Google Ads"
                  meta="Always through PPCWay's own developer token, never shared"
                />
                <ListRow title="Billing" meta="PPCWay bills Brightpath. You bill your clients." />
                <ListRow title="Support" meta="Your clients come to you first, then you to us" />
              </Rows>
            </Panel>
          </>
        }
      >
        <Panel title="Logo and colour" action={{ label: "Replace logo" }} tone="plain">
          <div className="mt-4 flex flex-wrap items-center gap-4">
            <span className="bg-ad-bg border-line flex h-14 items-center gap-[10px] rounded-[12px] border px-5">
              <span className="bg-brand inline-block size-[26px] rounded-[8px]" />
              <span className="text-ink text-[19px] font-bold">brightpath</span>
            </span>
            <p className="text-muted max-w-[380px] text-[14px] leading-[17px]">
              SVG or PNG, shown at the top of every client screen and on the first page of reports.
            </p>
          </div>
          <p className="text-muted mt-4 text-[13px] leading-4 font-semibold">Brand colour</p>
          <div className="mt-3 flex flex-wrap items-end gap-3">
            {swatches.map((c, i) => (
              <button
                key={c}
                type="button"
                aria-label={c}
                className="size-9 rounded-full border-2"
                style={{ background: c, borderColor: i === 0 ? "#0f1720" : "#fff" }}
              />
            ))}
            <label className="ml-2 block w-[130px]">
              <span className="text-muted block text-[13px] leading-4 font-semibold">Hex</span>
              <input
                defaultValue="#2F5BD3"
                className="border-line mt-[7px] h-[46px] w-full rounded-[12px] border px-[15px] text-[15px] outline-none"
              />
            </label>
          </div>
          <Footnote>
            We check contrast, so buttons and text stay readable whatever colour you pick.
          </Footnote>
        </Panel>
        <Panel title="Custom domain" action={{ label: "Check now" }} tone="plain">
          <FieldRow label="Where your clients sign in" value="app.brightpath.ca" />
          <p className="text-muted mt-3 text-[13px] leading-4 font-semibold">
            Add these two records where you manage brightpath.ca
          </p>
          <Rows className="mt-1">
            <ListRow
              title="CNAME · app → clients.ppcway.com"
              meta="Points your address at PPCWay"
              chip="Not seen yet"
              chipTone="amber"
            />
            <ListRow
              title="TXT · _ppcway → pw-verify-8f3k2q"
              meta="Proves the domain is yours"
              chip="Found"
              chipTone="pale"
            />
          </Rows>
          <Footnote>
            DNS changes can take up to a day. We check every 10 minutes and email you when it is
            live. Until then clients use brightpath.ppcway.com.
          </Footnote>
        </Panel>
        <Panel title="Report emails" tone="plain">
          <FieldRow label="Send reports from" value="reports@brightpath.ca" type="email" />
          <Rows className="mt-1">
            <ListRow
              title="Sender verified"
              meta="SPF and DKIM records found on 3 Sep"
              chip="Verified"
              chipTone="pale"
            />
          </Rows>
        </Panel>
      </Columns>
    </AppShell>
  );
}
