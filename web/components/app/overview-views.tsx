import { Button } from "@/components/ui/button";
import { AppShell, type Workspace } from "./shell";
import {
  ActivityRow,
  AdMock,
  Banner,
  BarChart,
  Columns,
  Footnote,
  Legend,
  ListRow,
  MiniBars,
  NoticeCard,
  PageHead,
  Panel,
  Quote,
  Rows,
  Segmented,
  Summary,
  Tile,
  Tiles,
} from "./blocks";
import type { OverviewView, ReportView } from "./view-names";

/*
  The Overview page, from the "V2 Dashboard · Desktop 1440" frames in the Overview
  section. Thirteen drawn states: the healthy month, its spend variant, the same
  month under three banners (automation paused for everyone, a support view, an
  agency viewer), the agency client Northgate, week one, and five broken states.
*/

const alpha: Workspace = { name: "Alpha Plumbing", meta: "Mississauga, Ontario" };
const weekBars = [99, 117, 108, 135, 126, 144, 117, 126].map((h) => h / 144);

export function OverviewView({ view }: { view: OverviewView }) {
  switch (view) {
    case "spend":
      return <HealthyMonth spend />;
    case "paused-everyone":
      return <HealthyMonth banner="paused" />;
    case "support":
      return <HealthyMonth banner="support" initials="RS" />;
    case "agency-view":
      return (
        <HealthyMonth
          banner="agency"
          initials="PS"
          workspace={{ name: "Alpha Plumbing", meta: "Client of Brightpath Media" }}
        />
      );
    case "northgate":
      return <Northgate />;
    case "week-one":
      return <WeekOne />;
    case "disconnected":
      return <Disconnected />;
    case "suspended":
      return <Suspended />;
    case "card-declined":
      return <CardDeclined />;
    case "no-tracking":
      return <NoTracking />;
    case "restaurant":
      return <Unsupported />;
    case "restricted":
      return <Restricted />;
    default:
      return <HealthyMonth />;
  }
}

/* ---------- 17:1445, 92:16499, 87:5561, 76:2922, 89:13753 ---------- */
function HealthyMonth({
  spend,
  banner,
  initials = "DW",
  workspace = alpha,
}: {
  spend?: boolean;
  banner?: "paused" | "support" | "agency";
  initials?: string;
  workspace?: Workspace;
}) {
  const readOnly = banner === "support" || banner === "agency";
  return (
    <AppShell active="overview" workspace={workspace} initials={initials}>
      {banner === "paused" ? (
        <Banner
          tag="Paused for everyone"
          text="Automatic changes are off for every account while we sort out an issue with Google. Your ads keep running."
          link={{ label: "What this means" }}
        />
      ) : banner === "support" ? (
        <Banner
          tag="Support view"
          text="Read only · you see Alpha Plumbing as Dana does · logged, and Dana was emailed"
          actions={
            <>
              <Button variant="secondary" size="sm">
                Ask for write access
              </Button>
              <Button size="sm" className="bg-rail hover:bg-rail-soft">
                Leave support view
              </Button>
            </>
          }
        />
      ) : banner === "agency" ? (
        <Banner
          tone="brand"
          tag="Brightpath · view only"
          text="You see everything Dana sees. Approvals, undo and settings stay with her team."
        />
      ) : null}
      <PageHead
        title="Your ads brought 58 calls this month."
        lead="That is 12 more than last month, and each one cost you $4.60 less. Nothing needs fixing today."
      />
      <Tiles>
        <Tile
          tone="brand"
          label="Cost per call"
          value="$21.40"
          chip="18% cheaper than last month"
        />
        <Tile label="Spent" value="$1,240" chip="$44 more than last month" />
        <Tile label="Calls" value="58" chip="12 more than last month" />
        <Tile label="Budget used" value="62%" progress={0.62} />
      </Tiles>
      <Columns
        aside={
          <>
            <NoticeCard
              tag="Waiting for you"
              title="Lower the daily budget from $40 to $32"
              body="Spend has run ahead of pace for six days. This keeps the month on budget without pausing anything."
              primary={{ label: "Approve" }}
              secondary={{ label: banner === "agency" ? "Remind Dana" : "Skip this" }}
              primaryTone={readOnly ? "secondary" : undefined}
            >
              {banner === "paused" ? (
                <p className="text-amber-dark order-last mt-4 text-[13px] leading-4 font-medium">
                  Approving still works. The change will go to Google once automatic changes
                  restart.
                </p>
              ) : banner === "support" ? (
                <p className="text-amber-dark order-last mt-4 text-[13px] leading-4 font-medium">
                  Buttons are off in support view. Only Dana can approve a budget change.
                </p>
              ) : banner === "agency" ? (
                <p className="text-amber-dark order-last mt-4 text-[13px] leading-4 font-medium">
                  Only Dana can approve a budget change. You can send a reminder; it goes from
                  Brightpath.
                </p>
              ) : null}
            </NoticeCard>
            <YourCampaigns />
          </>
        }
      >
        {spend ? (
          <Panel
            title="How your spend is trending"
            action={
              <div className="flex flex-wrap gap-2">
                <Segmented options={["Calls", "Spend"]} active="Spend" />
                <Segmented options={["30", "60", "90 days"]} active="30" />
              </div>
            }
          >
            <BarChart
              bars={[113, 121, 118, 128, 126, 132, 129, 96].map((h) => h / 132)}
              axisStart="Week of 14 July · $248"
              axisEnd="This week so far · $184"
              footnote="Each bar is one week's spend, never more than your $48 a day limit allows. You got 14 calls for this week's $184 so far."
            />
          </Panel>
        ) : (
          <Panel
            title="How your calls are trending"
            action={
              banner ? (
                <Legend label="This week" />
              ) : (
                <div className="flex flex-wrap gap-2">
                  <Segmented options={["Calls", "Spend"]} active="Calls" />
                  <Segmented options={["30", "60", "90 days"]} active="30" />
                </div>
              )
            }
          >
            <BarChart
              bars={weekBars}
              pill="14 calls"
              axisStart="Week of 14 July"
              footnote="Each bar is one week. This week is still running."
            />
          </Panel>
        )}
        <Panel
          title="What PPCWay did this week"
          action={{ label: "See everything", href: "/activity" }}
        >
          <Rows>
            {banner === "paused" ? (
              <ActivityRow
                icon="bars"
                iconTone="amber"
                title="Paused automatic changes for everyone."
                meta="Today 9:05 am · we email you the moment they restart"
                action="Details"
              />
            ) : (
              <ActivityRow
                icon="bars"
                iconTone="amber"
                title="Paused 3 search terms that spent $38 without a single call."
                meta="Applied Tuesday, saved about $38 a month"
                action="Undo"
                actionTone={readOnly ? undefined : "brand"}
              />
            )}
            <ActivityRow
              icon="plus"
              iconTone="brand"
              title={<>Added &ldquo;emergency plumber near me&rdquo; as a keyword.</>}
              meta="Applied Monday, after it brought 4 calls"
              action="Undo"
            />
            <ActivityRow
              icon="line"
              iconTone="grey"
              title="Kept your daily budget at $40."
              meta="Checked Sunday: a little ahead of pace, so we watched another day"
            />
          </Rows>
        </Panel>
      </Columns>
    </AppShell>
  );
}

function YourCampaigns({
  rows = [
    {
      name: "Plumbing repairs",
      meta: "41 calls, $20.98 each",
      chip: "Live",
      tone: "pale" as const,
    },
    {
      name: "Google Maps (Local)",
      meta: "17 calls, $19.77 each",
      chip: "Live",
      tone: "pale" as const,
    },
  ],
}: {
  rows?: { name: string; meta: string; chip: string; tone: "pale" | "grey" | "red" | "amber" }[];
}) {
  return (
    <Panel title="Your campaigns">
      <Rows className="mt-1">
        {rows.map((r) => (
          <ListRow key={r.name} title={r.name} meta={r.meta} chip={r.chip} chipTone={r.tone} dot />
        ))}
      </Rows>
    </Panel>
  );
}

/* ---------- 89:14118 ---------- */
function Northgate() {
  return (
    <AppShell
      active="overview"
      workspace={{ name: "Northgate HVAC", meta: "Brampton, Ontario" }}
      initials="JT"
    >
      <PageHead
        title="Your ads brought 61 calls this month."
        lead="That is $19.00 a call. Furnace repair searches picked up as the nights got cooler. Your account manager is Priya at Brightpath."
      />
      <Tiles>
        <Tile
          tone="brand"
          label="Cost per call"
          value="$19.00"
          chip="10% cheaper than last month"
        />
        <Tile label="Spent" value="$1,159" chip="$60 more than last month" />
        <Tile label="Calls" value="61" chip="9 more than last month" />
        <Tile label="Budget used" value="62%" progress={0.62} />
      </Tiles>
      <Columns
        aside={
          <>
            <NoticeCard
              tag="Waiting for you"
              title="Lower two bids that cost too much"
              body="Two furnace searches cost over $30 a call this month. Lowering their bids keeps you near $19 a call."
              primary={{ label: "Approve" }}
              secondary={{ label: "Skip this" }}
            />
            <YourCampaigns
              rows={[
                {
                  name: "Furnace repair",
                  meta: "44 calls, $18.20 each",
                  chip: "Live",
                  tone: "pale",
                },
                {
                  name: "Google Maps (Local)",
                  meta: "17 calls, settling in",
                  chip: "Learning",
                  tone: "grey",
                },
              ]}
            />
          </>
        }
      >
        <Panel title="How your calls are trending" action={<Legend label="This week" />}>
          <BarChart
            bars={weekBars}
            pill="16 calls"
            axisStart="Week of 14 July"
            footnote="Each bar is one week. This week is still running."
          />
        </Panel>
        <Panel
          title="What PPCWay did this week"
          action={{ label: "See everything", href: "/activity" }}
        >
          <Rows>
            <ActivityRow
              icon="bars"
              iconTone="amber"
              title="Blocked 3 searches for furnace parts that never called."
              meta="Applied Tuesday, saved about $38 a month"
              action="Undo"
            />
            <ActivityRow
              icon="plus"
              iconTone="brand"
              title="Added 'furnace repair near me' as a keyword."
              meta="Applied Monday, after it brought 4 calls"
              action="Undo"
            />
            <ActivityRow
              icon="line"
              iconTone="grey"
              title="Kept your daily budget at $39."
              meta="Checked Sunday: a little ahead of pace, so we watched another day"
            />
          </Rows>
        </Panel>
      </Columns>
    </AppShell>
  );
}

/* ---------- 81:2058 ---------- */
function WeekOne() {
  return (
    <AppShell active="overview" workspace={alpha} period="Since 4 Aug" badges={{}}>
      <PageHead
        title="Week one. Google is still learning who calls you."
        lead="Early numbers swing a lot, so we do not judge them yet. Most accounts settle in two to four weeks. This is what has happened so far."
      />
      <Tiles>
        <Tile tone="brand" label="Calls so far" value="3" chip="Normal for week one" />
        <Tile label="Spent so far" value="$168" chip="Of about $200 planned" />
        <Tile
          label="Cost per call"
          value="Too early"
          valueTone="faint"
          chip="Shown after 10 calls"
          chipTone="grey"
        />
        <Tile label="Google's learning" value="Day 5 of 14" progress={5 / 14} />
      </Tiles>
      <Columns
        aside={
          <>
            <NoticeCard
              tone="brand"
              tag="What to expect"
              title="Weeks 1 and 2 are for learning. Weeks 3 and 4 get steadier."
              body="From week 3 we compare each week with the one before and start suggesting changes. Your first Monday email arrives on 10 August."
              primary={{ label: "How it works" }}
              secondary={{ label: "Got it" }}
              className="border-amber-line"
            />
            <YourCampaigns
              rows={[
                {
                  name: "Plumbing repairs",
                  meta: "3 calls, learning",
                  chip: "Learning",
                  tone: "grey",
                },
                {
                  name: "Google Maps (Local)",
                  meta: "No calls yet, learning",
                  chip: "Learning",
                  tone: "grey",
                },
              ]}
            />
          </>
        }
      >
        <Panel title="Calls each day" action={<Legend label="Learning period" />}>
          <Summary>
            Three calls in five days, all from Mississauga. Google is showing your ad to different
            people each day while it works out who calls.
          </Summary>
          <MiniBars
            height={70}
            bars={[
              { h: 0.06 },
              { h: 0.63 },
              { h: 0.06 },
              { h: 0.63 },
              { h: 0.63, tone: "brand" },
              ...Array.from({ length: 9 }, () => ({ h: 0.06, tone: "empty" as const })),
            ]}
            labels={["Tue 4 Aug", "Today", "18 Aug, learning ends"]}
          />
        </Panel>
        <Panel
          title="What we are doing while it learns"
          action={{ label: "See everything", href: "/activity" }}
        >
          <Rows>
            <ActivityRow
              icon="bars"
              iconTone="amber"
              title="Holding bid changes until 18 August."
              meta="Changing bids now would restart Google's learning"
              action="Why"
            />
            <ActivityRow
              icon="plus"
              iconTone="brand"
              title="Blocked 4 searches that were not about plumbing."
              meta="Safety checks still run every day · saved about $9"
              action="See them"
            />
            <ActivityRow
              icon="line"
              iconTone="grey"
              title="Checked your budget every morning."
              meta="On pace: $168 of about $200 so far"
            />
          </Rows>
        </Panel>
      </Columns>
    </AppShell>
  );
}

/* ---------- 17:3295 ---------- */
function Disconnected() {
  return (
    <AppShell active="overview" workspace={alpha}>
      <PageHead
        title="We've lost our connection to Google."
        lead="Your ads are still running. We just can't see them, and we can't make any changes, until you reconnect."
      />
      <Tiles>
        <Tile
          tone="red"
          label="Disconnected"
          value="Since 4:12 pm"
          chip="Your ads are still running"
        />
        <Tile label="Still spending" value="$40 a day" chip="Nothing is being tuned" />
        <Tile label="Changes on hold" value="2" chip="They run when you reconnect" />
        <Tile label="Reconnecting takes" value="1 min" progress={1} />
      </Tiles>
      <ProblemPanel
        tag="Disconnected"
        title="What happened"
        body="Someone removed PPCWay's access to the Google Ads account today at 4:12 pm. That happens if a password changed, if the account owner revoked it, or if Google expired the permission. Everything we built is still in your own Google Ads account and stays there whatever you decide."
        primary="Reconnect to Google"
        secondary="Pause everything for now"
        note="If we stay disconnected for more than 3 days, PPCWay stops charging and credits those days."
      />
      <Panel tone="amber" title="Your PPCWay fee while we are cut off" className="mt-4">
        <p className="text-ink mt-2 text-[15px] leading-[18px]">
          If the connection stays down for more than 3 days, we stop charging and credit those days
          on your next bill. You never pay for work we cannot do.
        </p>
      </Panel>
    </AppShell>
  );
}

/** The full-width red-bordered panel used by the three "cannot continue" states. */
export function ProblemPanel({
  tag,
  tagTone = "red",
  title,
  body,
  primary,
  primaryTone = "red",
  secondary,
  note,
}: {
  tag: string;
  tagTone?: "red" | "amber";
  title: string;
  body: string;
  primary: string;
  primaryTone?: "red" | "brand";
  secondary: string;
  note: string;
}) {
  return (
    <section className="bg-panel border-red-line mt-[26px] rounded-[16px] border px-5 py-6 lg:px-[29px] lg:py-[27px]">
      <span
        className={cn(
          "inline-flex h-[26px] items-center rounded-full px-3 text-[13px] leading-4 font-semibold",
          tagTone === "red" ? "bg-red-pale text-red-strong" : "bg-amber-pale text-amber-dark",
        )}
      >
        {tag}
      </span>
      <h2 className="text-ink mt-[14px] text-[20px] leading-6 font-semibold">{title}</h2>
      <p className="text-muted mt-[14px] max-w-[1000px] text-[16px] leading-[19px]">{body}</p>
      <div className="mt-[22px] flex flex-wrap items-center gap-3">
        <Button className={primaryTone === "red" ? "bg-red-strong hover:bg-red" : undefined}>
          {primary}
        </Button>
        <Button variant="secondary" className="border-line">
          {secondary}
        </Button>
        <p className="text-faint text-[13px] leading-4">{note}</p>
      </div>
    </section>
  );
}

function cn(...parts: (string | false | undefined)[]) {
  return parts.filter(Boolean).join(" ");
}

/* ---------- 81:2255 ---------- */
function Suspended() {
  return (
    <AppShell active="overview" workspace={alpha} period="Today" badges={{}}>
      <PageHead
        title="Google suspended your account, so your ads are off."
        lead="This came from Google, not from PPCWay, and nothing is lost: campaigns, settings and history are all kept. Only you can appeal. Google usually answers in 3 to 5 working days."
      />
      <Tiles>
        <Tile
          label="Google Ads account"
          value="Suspended"
          valueTone="red"
          chip="Since 10:40 today"
          chipTone="red"
        />
        <Tile label="Ads showing" value="0" chip="None since 10:40" chipTone="grey" />
        <Tile label="Spent today" value="$11.20" chip="All before 10:40" chipTone="grey" />
        <Tile label="Automation" value="Paused" chip="Until Google lifts it" chipTone="grey" />
      </Tiles>
      <Columns
        aside={
          <>
            <NoticeCard
              tag="Only you can do this"
              title="Appeal on Google Ads"
              body="Sign in to Google Ads, open the notice and choose Submit an appeal. Have photo ID and a card statement ready. It takes about 10 minutes."
              primary={{ label: "Open Google Ads" }}
              secondary={{ label: "Talk to us" }}
            />
            <YourCampaigns
              rows={[
                {
                  name: "Plumbing repairs",
                  meta: "Stopped by Google at 10:40",
                  chip: "Suspended",
                  tone: "red",
                },
                {
                  name: "Google Maps (Local)",
                  meta: "Stopped by Google at 10:40",
                  chip: "Suspended",
                  tone: "red",
                },
              ]}
            />
          </>
        }
      >
        <Panel title="What Google said" action={<Legend label="From Google Ads" tone="red" />}>
          <Quote
            said="Suspicious payment activity. Google wants to confirm the card on the account belongs to Alpha Plumbing before any ads run again."
            then="This is common after a new card is added. Google asks for photo ID and a recent card statement. We cannot appeal for you, because Google only takes appeals from the account owner."
            note="We check Google twice a day. Last check 10:52."
          />
        </Panel>
        <Panel title="What we did" action={{ label: "See everything", href: "/activity" }}>
          <Rows>
            <ActivityRow
              icon="bars"
              iconTone="amber"
              title="Paused all automation."
              meta="10:52 today · nothing changes while you are suspended"
              action="Why"
            />
            <ActivityRow
              icon="plus"
              iconTone="brand"
              title="Kept every campaign and setting."
              meta="They restart as they were once Google lifts it"
              action="View"
            />
            <ActivityRow
              icon="line"
              iconTone="grey"
              title="Changed your Monday email."
              meta="It will explain the suspension instead of showing $0"
            />
          </Rows>
        </Panel>
      </Columns>
    </AppShell>
  );
}

/* ---------- 89:13937 ---------- */
function CardDeclined() {
  return (
    <AppShell active="overview" workspace={alpha} period="Today" badges={{}}>
      <PageHead
        title="Google declined your card, so your ads stopped."
        lead="Google could not charge the card on your Google Ads account at 6:12 am. PPCWay never sees that card, so only you can fix it, on Google's own billing page. Nothing else is lost."
      />
      <Tiles>
        <Tile
          label="Your ads"
          value="Stopped"
          valueTone="red"
          chip="Since 6:12 am"
          chipTone="red"
        />
        <Tile label="Calls today" value="0" chip="Ads are not showing" chipTone="grey" />
        <Tile label="The fix takes" value="3 minutes" chip="On Google's site" chipTone="grey" />
        <Tile label="Our changes" value="On hold" chip="Until your card works" chipTone="grey" />
      </Tiles>
      <Columns
        aside={
          <>
            <NoticeCard
              tag="Only you can do this"
              title="Update your card on Google"
              body="Open Google Ads billing, add a working card, and your ads start again within the hour."
              primary={{ label: "Open Google billing" }}
              secondary={{ label: "Talk to us" }}
            />
            <YourCampaigns
              rows={[
                {
                  name: "Plumbing repairs",
                  meta: "Stopped by Google at 6:12 am",
                  chip: "Stopped",
                  tone: "red",
                },
                {
                  name: "Google Maps (Local)",
                  meta: "Stopped by Google at 6:12 am",
                  chip: "Stopped",
                  tone: "red",
                },
              ]}
            />
          </>
        }
      >
        <Panel title="What Google said" action={<Legend label="From Google Ads" tone="red" />}>
          <Quote
            said="Payment declined. Google will try the card again, but your ads stay off until a charge goes through."
            then="This is the card for your ads, which Google bills directly. It is separate from your PPCWay plan, which is paid and fine."
          />
        </Panel>
        <Panel title="What we did" action={{ label: "See everything", href: "/activity" }}>
          <Rows>
            <ActivityRow
              icon="bars"
              iconTone="amber"
              title="Held every change."
              meta="6:20 am · changes would not reach Google anyway"
              action="Why"
            />
            <ActivityRow
              icon="plus"
              iconTone="brand"
              title="Emailed you straight away."
              meta="6:20 am, to Dana and the office inbox"
              action="See it"
            />
            <ActivityRow
              icon="line"
              iconTone="grey"
              title="Left today's numbers out."
              meta="Your Monday email will explain the stop instead"
            />
          </Rows>
        </Panel>
      </Columns>
    </AppShell>
  );
}

/* ---------- 87:5363 ---------- */
function NoTracking() {
  return (
    <AppShell active="overview" workspace={alpha}>
      <PageHead
        title="Calls stopped being counted on Monday. Your ads are still running."
        lead="Google has not recorded a call since 5:40 pm Monday, but your ads kept getting clicks. Until calls count again we hold every bid change, because we would be steering blind."
      />
      <Tiles>
        <Tile
          label="Calls counted"
          value="0 since Mon"
          valueTone="red"
          chip="Usually 2 a day"
          chipTone="red"
        />
        <Tile label="Clicks since Monday" value="46" chip="Ads running normally" chipTone="grey" />
        <Tile label="Spent since Monday" value="$96" chip="Normal pace" chipTone="grey" />
        <Tile label="Bid changes" value="On hold" chip="Until calls count again" chipTone="amber" />
      </Tiles>
      <Columns
        aside={
          <>
            <NoticeCard
              tag="Needs you"
              title="Turn call reporting back on?"
              body="Someone switched it off in Google Ads on Monday at 5:40 pm. We can turn it back on for you now, and it shows in Activity with an undo."
              primary={{ label: "Turn it on" }}
              secondary={{ label: "I'll check first" }}
            />
            <YourCampaigns
              rows={[
                {
                  name: "Plumbing repairs",
                  meta: "Clicks normal, calls not counted",
                  chip: "No tracking",
                  tone: "amber",
                },
                {
                  name: "Google Maps (Local)",
                  meta: "Clicks normal, calls not counted",
                  chip: "No tracking",
                  tone: "amber",
                },
              ]}
            />
          </>
        }
      >
        <Panel title="Calls counted each day" action={<Legend label="Last 14 days" tone="red" />}>
          <Summary>
            Calls fell to zero overnight while clicks stayed level. That almost always means
            tracking broke, not that people stopped calling.
          </Summary>
          <MiniBars
            bars={[
              ...[52, 26, 78, 52, 52, 26, 52, 78, 52, 52, 26].map((h) => ({ h: h / 78 })),
              { h: 0.07, tone: "red" as const },
              { h: 0.07, tone: "red" as const },
              { h: 0.07, tone: "red" as const },
            ]}
            labels={["28 Aug", undefined, "Today"]}
          />
        </Panel>
        <Panel title="What we did" action={{ label: "See everything", href: "/activity" }}>
          <Rows>
            <ActivityRow
              icon="bars"
              iconTone="amber"
              title="Held every bid change."
              meta="Wed 6:00 am · after two days of clicks with no calls"
              action="Why"
            />
            <ActivityRow
              icon="plus"
              iconTone="brand"
              title="Checked your tracking number."
              meta="(905) 555-0142 still forwards to your phone"
              action="Test"
            />
            <ActivityRow
              icon="line"
              iconTone="grey"
              title="Found the likely cause."
              meta="Call reporting was switched off in Google Ads, Monday 5:40 pm"
            />
          </Rows>
        </Panel>
      </Columns>
    </AppShell>
  );
}

/* ---------- 87:8453 ---------- */
function Unsupported() {
  return (
    <AppShell
      active="overview"
      workspace={{ name: "Maple Street Bistro", meta: "Hamilton, Ontario" }}
      initials="MB"
      badges={{}}
    >
      <PageHead
        title="Restaurants are not supported yet."
        lead="PPCWay works best today for trades, home services, practices and online shops. Restaurants need table bookings and store visits counted, which we are building next."
      />
      <Tiles>
        <Tile
          label="Setup paused"
          value="At step 3"
          chip="Nothing has been charged"
          chipTone="grey"
        />
        <Tile label="Your business" value="Restaurant" chip="Maple Street Bistro" />
        <Tile label="Expected" value="Early 2027" chip="We are building it now" />
        <Tile label="Already waiting" value="38" progress={1} />
      </Tiles>
      <ProblemPanel
        tag="You can join them"
        tagTone="amber"
        title="What we need to build first"
        body="Restaurants win customers through bookings, Maps and walk-ins. Counting those properly takes more than the call and form tracking we use for trades, so we would rather wait than run ads we cannot measure."
        primary="Join the waitlist"
        primaryTone="brand"
        secondary="What works today"
        note="We email you once, when restaurants open. Nothing is charged in the meantime."
      />
    </AppShell>
  );
}

/* ---------- 17:3483 ---------- */
function Restricted() {
  return (
    <AppShell active="overview" workspace={alpha} badges={{}}>
      <PageHead
        title="We can't advertise this kind of work yet."
        lead="Google has extra rules for some trades, and PPCWay doesn't handle them yet. Nothing has been charged and no ads have run."
      />
      <Tiles>
        <Tile tone="red" label="Setup stopped" value="At step 3" chip="Nothing has been charged" />
        <Tile label="What we found" value="Lending" chip="Payday loans and short term credit" />
        <Tile label="Google needs" value="A licence" chip="We can't collect it for you" />
        <Tile label="A person replies within" value="1 day" progress={1} />
      </Tiles>
      <ProblemPanel
        tag="Can't continue"
        title="Why we stopped"
        body="Reading alphaplumbing.ca, we found pages offering payday loans and short term credit alongside the plumbing work. Google treats consumer lending as a restricted category. It needs licences and certificates that PPCWay cannot collect on your behalf. If we have read your site wrongly, tell us and a person will look at it within one working day."
        primary="This looks wrong, ask someone"
        secondary="Read Google's rules"
        note="Your account stays open, and nothing is charged."
      />
    </AppShell>
  );
}

/* ---------- 67:608 and 81:2437, the report page ---------- */
export function ReportView({ view }: { view: ReportView }) {
  const dates = view === "dates";
  return (
    <AppShell active="overview" workspace={alpha}>
      {dates ? (
        <PageHead
          title="Pick any dates for the report."
          lead="Choose a preset or drag across the calendar. Google can revise the last two or three days as late calls come in, so recent days may change a little."
        />
      ) : (
        <PageHead
          title="Reports you can keep, print or send on."
          lead="Choose the dates and what goes in. Download a PDF to read, or a CSV for your accountant. Every number comes straight from Google Ads."
        />
      )}
      <Tiles>
        {dates ? (
          <>
            <Tile tone="brand" label="Dates" value="Since launch" chip="4 Aug to 9 Sep · 37 days" />
            <Tile label="Calls" value="62" chip="4 in the first week" />
            <Tile label="Spent" value="$1,470" chip="About $40 a day" />
            <Tile label="Cost per call" value="$23.71" progress={168 / 226} />
          </>
        ) : (
          <>
            <Tile tone="brand" label="Dates" value="Last 30 days" chip="11 Aug to 9 Sep · change" />
            <Tile label="Calls" value="58" chip="Up 12 on the 30 before" />
            <Tile label="Spent" value="$1,240" chip="About $41 a day" />
            <Tile label="Cost per call" value="$21.40" progress={180 / 226} />
          </>
        )}
      </Tiles>
      <Columns
        aside={
          <>
            <NoticeCard
              tone="brand"
              tag="Scheduled"
              title="Send this every month"
              body="On the 1st of each month we email a PDF of the month before to you and anyone you add. Your weekly email is separate and stays on."
              primary={{ label: "Set up monthly" }}
              secondary={{ label: "Not now" }}
            />
            <Panel title="Saved reports">
              <Rows className="mt-1">
                <ListRow
                  title="August 2026"
                  meta="PDF · emailed 1 Sep"
                  chip="Sent"
                  chipTone="pale"
                  dot
                />
                <ListRow
                  title="Launch report"
                  meta="What we built · 4 Aug"
                  chip="Saved"
                  chipTone="pale"
                  dot
                />
              </Rows>
            </Panel>
          </>
        }
      >
        {dates ? (
          <DatePicker />
        ) : (
          <Panel title="In one paragraph" action={{ label: "Goes on page one", tone: "brand" }}>
            <Summary>
              Your campaigns brought 58 calls for $1,240, which is $21.40 a call and $4.60 cheaper
              than the month before. Plumbing repairs did most of the work. We made 14 changes, you
              approved every one, and you undid one.
            </Summary>
          </Panel>
        )}
        <Panel title="What goes in the report" action={{ label: "Choose sections" }}>
          <Rows>
            <ActivityRow
              icon="bars"
              iconTone="brand"
              title="Summary, in plain English"
              meta="The paragraph above, plus the week by week trend"
              action="Included"
            />
            <ActivityRow
              icon="plus"
              iconTone="brand"
              title="Every change we made"
              meta="14 changes, each with its reason and what happened next"
              action="Included"
            />
            <ActivityRow
              icon="line"
              iconTone="brand"
              title="Full Google Ads figures"
              meta="Off · clicks, impressions, cost and conversions, by keyword and by day"
            />
          </Rows>
        </Panel>
        <Panel title="Download" action={{ label: "Email it instead" }}>
          <AdMock
            kicker="PDF · 6 pages"
            source={
              dates ? "Alpha Plumbing, 4 Aug to 9 Sep 2026" : "Alpha Plumbing, 11 Aug to 9 Sep 2026"
            }
            headline="For reading, or sending to a business partner"
            body="Need the raw numbers? The CSV has one row per keyword per day with the standard Google Ads columns, ready for your accountant or your own spreadsheet."
          >
            <div className="mt-4 flex flex-wrap gap-[10px]">
              <Button size="sm">Download PDF</Button>
              <Button size="sm" variant="secondary">
                Download CSV
              </Button>
            </div>
          </AdMock>
          <Footnote>
            {dates
              ? "Google can revise the last two or three days as late conversions come in."
              : "Google can revise the last two or three days as late calls come in. Your own records may differ too: Google counts only calls from your ads that last over 30 seconds."}
          </Footnote>
        </Panel>
      </Columns>
    </AppShell>
  );
}

const presets = [
  "Last 7 days",
  "Last 30 days",
  "This month",
  "Last month",
  "Since launch",
  "Custom",
];

function DatePicker() {
  return (
    <Panel title="Choose dates" action={{ label: "Custom range", tone: "brand" }}>
      <div className="mt-[18px] flex flex-col gap-5 md:flex-row">
        <ul className="flex flex-row flex-wrap gap-1 md:w-[150px] md:flex-col">
          {presets.map((p) => (
            <li key={p}>
              <button
                type="button"
                className={cn(
                  "h-[34px] w-full rounded-[8px] px-3 text-left text-[14px] leading-[17px] font-medium",
                  p === "Since launch"
                    ? "bg-brand-pale text-brand-dark"
                    : "text-ink hover:bg-line-soft",
                )}
              >
                {p}
              </button>
            </li>
          ))}
        </ul>
        <Month name="August 2026" first={5} days={31} from={4} />
        <Month name="September 2026" first={1} days={30} to={9} />
      </div>
      <div className="mt-[18px] flex flex-wrap items-center justify-between gap-3">
        <p className="text-ink text-[14px] leading-[17px] font-semibold">
          4 Aug to 9 Sep · 37 days
        </p>
        <div className="flex gap-[10px]">
          <Button size="sm" variant="secondary">
            Cancel
          </Button>
          <Button size="sm">Apply</Button>
        </div>
      </div>
    </Panel>
  );
}

function Month({
  name,
  first,
  days,
  from,
  to,
}: {
  name: string;
  first: number;
  days: number;
  from?: number;
  to?: number;
}) {
  const cells = [
    ...Array.from({ length: first }, () => null),
    ...Array.from({ length: days }, (_, i) => i + 1),
  ];
  while (cells.length % 7) cells.push(null);
  return (
    <div className="w-full md:w-[238px]">
      <p className="text-ink text-[14px] leading-[17px] font-semibold">{name}</p>
      <div className="text-faint mt-2 grid grid-cols-7 text-center text-[11px] leading-[13px] font-semibold">
        {["M", "T", "W", "T", "F", "S", "S"].map((d, i) => (
          <span key={i}>{d}</span>
        ))}
      </div>
      <div className="mt-1 grid grid-cols-7 gap-y-1 text-center">
        {cells.map((d, i) => {
          const inRange =
            d !== null && (from === undefined || d >= from) && (to === undefined || d <= to);
          const edge = d !== null && (d === from || d === to);
          return (
            <span
              key={i}
              className={cn(
                "flex h-8 items-center justify-center text-[13px] leading-4",
                d === null
                  ? ""
                  : inRange
                    ? edge
                      ? "bg-brand rounded-[8px] font-semibold text-white"
                      : "bg-brand-pale text-brand-dark"
                    : "text-ink",
              )}
            >
              {d ?? ""}
            </span>
          );
        })}
      </div>
    </div>
  );
}
