import type { EmailSpec } from "./email";

/* One entry per "V2 · Email" frame, two emails each. */
export const EMAIL_SETS = {
  monday: {
    title: "The Monday email",
    lead: "Short on purpose: what happened, what we did, and one thing to do. When the account is broken, the email says so instead of sending numbers that would mislead.",
    emails: [
      {
        caption: "A normal week",
        date: "Week of 31 Aug to 6 Sep",
        headline: "Good week, Dana. 13 calls for $282.",
        sentence:
          "That is 2 more calls than the week before, and each one cost about $3 less. Burst pipes brought in 6 of them.",
        stats: [
          { label: "Calls", value: "13", tone: "brand" },
          { label: "Spent", value: "$282" },
          { label: "Per call", value: "$21.69" },
        ],
        section: "What we did",
        items: [
          "Blocked 2 searches that never called, after you approved them.",
          "Raised the bid on burst pipe searches by 10%, inside your $14 cap.",
          "Checked your call tracking every day. Every call was counted.",
        ],
        action: {
          text: "2 changes are waiting for your yes, including blocking 3 searches that cost $38 and never brought a call.",
          button: "Review 2 changes",
          box: "amber",
        },
        footer: "You get this every Monday. Choose what we send, or stop it, in Settings.",
      },
      {
        caption: "A week where something broke",
        date: "Week of 31 Aug to 6 Sep",
        headline: "Your ads stopped on Thursday.",
        sentence:
          "Google declined your card on 3 September, so your ads have not shown since. That is why the calls stopped. The campaign itself is fine.",
        stats: [
          { label: "Ads", value: "Stopped", tone: "red" },
          { label: "Since", value: "Thu 3 Sep" },
          { label: "The fix takes", value: "3 minutes" },
        ],
        section: "What we did",
        dot: "red",
        items: [
          "Paused every change until your ads are running again.",
          "Emailed you on Thursday and again on Friday.",
          "Left this week's numbers out. They would only show the outage.",
        ],
        action: {
          text: "Update your card on Google's own billing page. Only you can, and your ads usually start again within an hour.",
          button: "Update card on Google",
          tone: "red",
          box: "red",
        },
        footer: "You get this every Monday. Choose what we send, or stop it, in Settings.",
      },
    ],
  },
  "monday-special": {
    title: "The Monday email, special weeks",
    lead: "The digest changes shape when the numbers would mislead: while Google learns, and when tracking breaks.",
    emails: [
      {
        caption: "In the first weeks",
        date: "Mon 10 Aug",
        headline: "Week one: 3 calls while Google learns",
        sentence:
          "Early numbers swing, so we do not judge them yet. Most accounts settle in two to four weeks.",
        stats: [
          { label: "Calls", value: "3", tone: "brand" },
          { label: "Spent", value: "$168" },
          { label: "Learning", value: "Day 7 of 14" },
        ],
        section: "What we did",
        items: [
          "Held bid changes while Google learns",
          "Blocked 4 searches that were not about plumbing",
          "Checked your budget every morning",
        ],
        action: { text: "Nothing to do this week.", button: "See your dashboard", box: "brand" },
      },
      {
        caption: "When tracking is broken",
        date: "Mon 14 Sep",
        headline: "Calls were not counted this week",
        sentence:
          "Tracking stopped on Monday, so this week's numbers would mislead you. We have left them out.",
        stats: [
          { label: "Calls counted", value: "0", tone: "red" },
          { label: "Clicks", value: "46" },
          { label: "Bid changes", value: "Held" },
        ],
        section: "What we did",
        dot: "red",
        items: [
          "Held every bid change",
          "Found the cause: call reporting was switched off",
          "Emailed you on Wednesday",
        ],
        action: {
          text: "Switch call reporting back on and next week's email is back to normal.",
          button: "Fix tracking",
          box: "red",
        },
      },
    ],
  },
  "monday-stale": {
    title: "The Monday email, two more special weeks",
    lead: "When the numbers are late or the account is off, the email says so instead of printing zeros.",
    emails: [
      {
        caption: "When Google's numbers are late",
        date: "Mon 21 Sep",
        headline: "This week's numbers are not in yet",
        sentence:
          "Google's reports for Friday and Saturday have not arrived. Rather than show you half a week, we have left the numbers out.",
        stats: [
          { label: "Calls", value: "Late", tone: "amber" },
          { label: "Last full day", value: "Thursday" },
          { label: "We try again", value: "Every 6 hours" },
        ],
        section: "What we did",
        dot: "amber",
        items: [
          "Kept checking your budget and your ads",
          "Made no changes on part of the data",
          "Will send the full week once it arrives",
        ],
        action: {
          text: "Nothing to do. Your ads ran normally.",
          button: "See what we have",
          box: "amber",
        },
      },
      {
        caption: "When the account was suspended",
        date: "Mon 14 Sep",
        headline: "Your ads have been off since Thursday",
        sentence:
          "Google suspended the account on Thursday over suspicious payment activity. There are no numbers worth showing until it is lifted.",
        stats: [
          { label: "Ads", value: "Off", tone: "red" },
          { label: "Since", value: "Thu 10:40" },
          { label: "Appeal sent", value: "Not yet" },
        ],
        section: "What we did",
        dot: "red",
        items: [
          "Paused every change the same morning",
          "Kept your campaigns and settings as they were",
          "Emailed you on Thursday and Friday",
        ],
        action: {
          text: "Only you can appeal, in Google Ads. It takes about 10 minutes.",
          button: "Open Google Ads",
          tone: "red",
          box: "red",
        },
      },
    ],
  },
  alerts: {
    title: "Alert emails",
    lead: "Sent the moment something needs a person. One job per email, with the one button that does it. Critical ones cannot be switched off.",
    emails: [
      {
        caption: "A change needs your OK",
        date: "Tuesday 8 Sep, 9:02 am",
        headline: "Lower your daily budget from $40 to $32?",
        sentence:
          "Spend has run ahead of pace for six days. This keeps the month on budget without pausing anything.",
        stats: [
          { label: "Now", value: "$40 a day", tone: "amber" },
          { label: "After", value: "$32 a day" },
          { label: "Saves each month", value: "$240" },
        ],
        section: "Why we suggest it",
        dot: "amber",
        items: [
          "You spent $276 in six days against about $240 planned.",
          "Calls held steady at 2 a day, so the extra money bought nothing.",
          "Nothing changes unless you say yes. It expires on 15 Sep.",
        ],
        action: {
          text: "Approve it here or in PPCWay. Either way it shows in your activity feed with an undo.",
          button: "Approve $32 a day",
          skip: "Skip this",
          box: "amber",
        },
        footer:
          "You get these because you can approve changes for Alpha Plumbing. Choose alerts in Settings.",
      },
      {
        caption: "Critical, sent straight away",
        date: "Friday 11 Sep, 7:15 am",
        headline: "PPCWay lost access to your Google Ads.",
        sentence:
          "Someone removed PPCWay's access in Google Ads at 7:12 this morning. Your ads are still running as they were, but we cannot see results or protect your budget until you reconnect.",
        stats: [
          { label: "Access", value: "Removed", tone: "red" },
          { label: "Your ads", value: "Still running" },
          { label: "Reconnecting takes", value: "1 minute" },
        ],
        section: "What we did",
        dot: "red",
        items: [
          "Stopped every change, because we cannot check them.",
          "Kept your settings and history, so nothing is lost.",
          "We will email again tonight if it is still off.",
        ],
        action: {
          text: "Reconnect with the same Google account as before. PPCWay asks for the same permissions, nothing more.",
          button: "Reconnect Google",
          tone: "red",
          box: "red",
        },
        footer:
          "Alerts about money or your account always come by email. You cannot turn these off.",
      },
    ],
  },
  "sign-in": {
    title: "Sign-in emails",
    lead: "Plain, short and safe: one link, what it does, and what to do if it was not you.",
    emails: [
      {
        caption: "After sign up",
        date: "Just now",
        headline: "Confirm your email to start",
        sentence: "Tap the button to confirm dana@alphaplumbing.ca. The link works for 24 hours.",
        action: {
          text: "Did not sign up for PPCWay? Ignore this and nothing happens.",
          button: "Confirm my email",
        },
        footer: "PPCWay · Mississauga, Ontario",
      },
      {
        caption: "When someone asks for a new password",
        date: "Just now",
        headline: "Reset your password",
        sentence:
          "Someone asked to reset the password for dana@alphaplumbing.ca. The link works once, for one hour.",
        action: {
          text: "Did not ask? Your password has not changed. Tell us if this keeps happening.",
          button: "Choose a new password",
        },
        footer: "A new password signs you out on every other device.",
      },
    ],
  },
  team: {
    title: "Team emails",
    lead: "Who joined, and who looked. Support access is always read-only unless you are told otherwise.",
    emails: [
      {
        caption: "Invitation",
        date: "7 Sep, 3:12 pm",
        headline: "Dana invited you to Alpha Plumbing",
        sentence:
          "You would see how the ads are doing and approve the changes PPCWay suggests. Budgets and billing stay with Dana.",
        stats: [
          { label: "Your role", value: "Team member", tone: "brand" },
          { label: "Expires", value: "14 Sep" },
        ],
        action: {
          text: "Accept to make a sign-in, or use your Google account.",
          button: "Accept invitation",
          box: "brand",
        },
        footer: "Not expecting this? You can ignore it.",
      },
      {
        caption: "When support looks at your account",
        date: "Today, 10:32 am",
        headline: "Sam from PPCWay support looked at your account",
        sentence:
          "You asked why a bid went down, so Sam opened a read-only view at 10:12 am. Nothing was changed.",
        section: "What that means",
        dot: "grey",
        items: [
          "Read only: Sam could not change anything",
          "Logged: it is in your account's access log",
          "Ended at 10:31 am",
        ],
        action: {
          text: "Did not ask for help? Tell us and we will find out why.",
          button: "See the access log",
        },
      },
    ],
  },
  launch: {
    title: "Launch emails",
    lead: "The two moments that matter most: billing is ready, and the ads are live.",
    emails: [
      {
        caption: "When Google confirms your card",
        date: "4 Aug, 3:06 pm",
        headline: "Google confirmed your card. You can launch.",
        sentence:
          "Everything else was ready before you left. One click and your campaign goes to Google for review.",
        action: {
          text: "Launching takes about 20 seconds.",
          button: "Launch my campaign",
          box: "brand",
        },
      },
      {
        caption: "When Google approves the ads",
        date: "4 Aug, 4:41 pm",
        headline: "You are live. Google approved your ads.",
        sentence:
          "Plumbing repairs and Google Maps (Local) started showing at 4:40 pm. The first two to four weeks are for learning, so early numbers will swing.",
        stats: [
          { label: "Daily budget", value: "$40", tone: "brand" },
          { label: "Your limit", value: "$48" },
          { label: "Ask first", value: "On" },
        ],
        action: {
          text: "Your first Monday email arrives on 10 August.",
          button: "Open your dashboard",
          box: "brand",
        },
      },
    ],
  },
  problems: {
    title: "Ad and account problems",
    lead: "Google said no. One email says what, why and the one thing to do.",
    emails: [
      {
        caption: "When a refused ad needs your pick",
        date: "Today, 7:41 am",
        headline: "Google turned down one of your headlines",
        sentence:
          "'The Best Drain Service in Town' needs proof Google can check. Your other headlines keep the ad running.",
        section: "What we suggest",
        dot: "amber",
        items: [
          "Our pick: 'Same-Day Drain Service'",
          "Two more options are ready in PPCWay",
          "Nothing changes until you choose",
        ],
        action: { text: "Pick a fix with one tap.", button: "Use our pick", box: "amber" },
      },
      {
        caption: "Critical, cannot be turned off",
        date: "Today, 10:52 am",
        headline: "Google suspended your account. Your ads are off.",
        sentence:
          "Google flagged suspicious payment activity at 10:40 am. Nothing is lost, but only you can appeal.",
        stats: [
          { label: "Ads", value: "Off", tone: "red" },
          { label: "Since", value: "10:40 am" },
          { label: "Appeal takes", value: "10 min" },
        ],
        action: {
          text: "Sign in to Google Ads and submit an appeal with photo ID and a card statement.",
          button: "Open Google Ads",
          tone: "red",
          box: "red",
        },
      },
    ],
  },
  money: {
    title: "Money emails",
    lead: "When spend stops, or is about to run out for the day.",
    emails: [
      {
        caption: "Critical, cannot be turned off",
        date: "Thu 3 Sep, 6:20 am",
        headline: "Google declined your card. Your ads stopped.",
        sentence:
          "Google could not charge the card on your Google Ads account at 6:12 am, so it paused your ads. PPCWay never sees this card.",
        stats: [
          { label: "Ads", value: "Stopped", tone: "red" },
          { label: "Since", value: "6:12 am" },
          { label: "Fix takes", value: "3 minutes" },
        ],
        action: {
          text: "Update the card on Google's own billing page.",
          button: "Update card on Google",
          tone: "red",
          box: "red",
        },
      },
      {
        caption: "When 90% of a day's budget is gone by 3 pm",
        date: "Today, 1:42 pm",
        headline: "Today's budget is almost gone",
        sentence:
          "$36 of your $40 was spent by 1:40 pm, mostly on emergency searches. Your ads stop for the day when it runs out.",
        stats: [
          { label: "Spent", value: "$36", tone: "amber" },
          { label: "Budget", value: "$40" },
          { label: "Your limit", value: "$48" },
        ],
        action: {
          text: "Raise today to $48, your limit? It goes back to $40 tomorrow.",
          button: "Raise to $48 today",
          box: "amber",
        },
        footer: "On Ask first nothing changes unless you tap.",
      },
    ],
  },
  tracking: {
    title: "Tracking and billing emails",
    lead: "The two failures that quietly waste money: calls not counted, and PPCWay's own payment.",
    emails: [
      {
        caption: "Critical, cannot be turned off",
        date: "Wed, 6:04 am",
        headline: "Calls stopped being counted on Monday",
        sentence:
          "Your ads are still running, but Google has not recorded a call since 5:40 pm Monday. We have held every bid change until it works again.",
        section: "What we did",
        dot: "amber",
        items: [
          "Held every bid change",
          "Checked your tracking number: it works",
          "Found it: call reporting was switched off in Google Ads",
        ],
        action: {
          text: "We can switch call reporting back on for you.",
          button: "Turn it back on",
          box: "amber",
        },
      },
      {
        caption: "Critical, cannot be turned off",
        date: "Thu 1 Oct, 9:00 am",
        headline: "Your PPCWay payment did not go through",
        sentence:
          "We could not charge $99 to the Visa ending 4242. This is for PPCWay only; your ads keep running.",
        stats: [
          { label: "Owed", value: "$99", tone: "red" },
          { label: "Next try", value: "3 Oct" },
          { label: "Pauses on", value: "8 Oct" },
        ],
        action: {
          text: "Update your card and we charge it straight away.",
          button: "Update card",
          tone: "red",
          box: "red",
        },
      },
    ],
  },
  privacy: {
    title: "Privacy emails",
    lead: "Your data, when you ask for it, and when you ask us to delete it.",
    emails: [
      {
        caption: "When your export is ready",
        date: "Today, 11:05 am",
        headline: "Your data is ready to download",
        sentence:
          "Everything we hold for Alpha Plumbing: your details, campaigns, every change and your results, as CSV and JSON files.",
        stats: [
          { label: "Files", value: "6", tone: "brand" },
          { label: "Size", value: "4.2 MB" },
          { label: "Link lasts", value: "7 days" },
        ],
        action: {
          text: "The link only works while you are signed in.",
          button: "Download",
          box: "brand",
        },
      },
      {
        caption: "When you delete your account",
        date: "Today, 11:20 am",
        headline: "We are deleting your PPCWay account",
        sentence:
          "We stopped all changes and removed our access to Google Ads today. Your campaigns are still in your Google account.",
        section: "What happens next",
        dot: "grey",
        items: [
          "Your details, settings and reports are erased within 30 days",
          "The record of changes stays 7 years, without your personal details",
          "Changed your mind? Reply within 30 days",
        ],
        action: {
          text: "Your ads keep running in Google Ads until you pause them there.",
          button: "Open Google Ads",
        },
      },
    ],
  },
  category: {
    title: "Category review emails",
    lead: "When onboarding stops for a restricted category and the owner asks for a second look.",
    emails: [
      {
        caption: "When the owner asks for a review",
        date: "8 Sep, 2:14 pm",
        headline: "A person is checking your business",
        sentence:
          "Google has extra rules for locksmiths. You sent your verification email, so one of our team reviews it within 2 working days.",
        section: "Meanwhile",
        dot: "amber",
        items: [
          "Nothing is charged while we look",
          "Your answers so far are saved",
          "We email you either way",
        ],
        action: {
          text: "Nothing to do until you hear from us.",
          button: "See your request",
          box: "amber",
        },
      },
      {
        caption: "When the review says yes",
        date: "10 Sep, 11:02 am",
        headline: "Good news: you can carry on",
        sentence:
          "Google verified Keyway Locksmiths on 8 September, and the name matches your Google Ads account. Setup is open again.",
        section: "What comes with it",
        items: [
          "Every ad uses your verified business name",
          "A stricter checker reads every line first",
          "We review the decision again in 12 months",
        ],
        action: {
          text: "Pick up where you left off, at step 3.",
          button: "Continue setup",
          box: "brand",
        },
      },
    ],
  },
  platform: {
    title: "Platform notices",
    lead: "Rare, sent to everyone at once, and written so nobody panics.",
    emails: [
      {
        caption: "When PPCWay pauses everyone",
        date: "Today, 9:06 am",
        headline: "We have paused automatic changes for every account",
        sentence:
          "Google flagged an issue with the tool we use to reach your account. Until it is sorted, PPCWay will not change anything. Your ads keep running exactly as they are.",
        section: "What this means",
        dot: "amber",
        items: [
          "Nothing is lost or changed",
          "Approvals still work and wait for the restart",
          "We email you the moment changes restart",
        ],
        action: { text: "No action needed from you.", button: "Read the update", box: "amber" },
      },
      {
        caption: "Template: if data is ever exposed",
        date: "Sent within 72 hours",
        headline: "A security problem affected your account",
        sentence:
          "Someone got into a PPCWay system that holds business contact details. Your Google Ads account and your card were not affected.",
        section: "What happened",
        dot: "red",
        items: [
          "Exposed: business name, email address and phone number",
          "Done: closed the gap, reset access, told the Privacy Commissioner",
          "For you: watch for emails pretending to be us",
        ],
        action: {
          text: "We will never ask for your password or a card number by email.",
          button: "Read the full notice",
          tone: "red",
          box: "red",
        },
      },
    ],
  },
  closed: {
    title: "Account closed, and an agency-branded email",
    lead: "The last email a leaving owner gets, and what a Brightpath client sees on Mondays.",
    emails: [
      {
        caption: "30 days after a deletion request",
        date: "10 Oct, 9:00 am",
        headline: "Your PPCWay data has been deleted",
        sentence:
          "As promised when you asked on 10 September, your details, settings, reports and team access are gone.",
        section: "What is left",
        dot: "grey",
        items: [
          "Kept, without your details: the record of changes, for 7 years",
          "Kept, as the law needs: invoices, for 7 years",
          "Your campaigns are still in your own Google Ads account",
        ],
        action: { text: "Thanks for using PPCWay. You are welcome back any time." },
        footer: "This is the last email we will send to this address.",
      },
      {
        caption: "A Brightpath client's Monday email",
        brand: "brightpath",
        date: "Mon 7 Sep",
        headline: "Good week: 16 calls for $301",
        sentence:
          "Furnace repair searches are picking up as the nights get cooler, and your cost per call fell to $18.80.",
        stats: [
          { label: "Calls", value: "16" },
          { label: "Spent", value: "$301" },
          { label: "Per call", value: "$18.80" },
        ],
        section: "What we did",
        dot: "grey",
        items: [
          "Blocked 3 searches for furnace parts",
          "Added 'furnace repair near me' as a keyword",
          "Checked call tracking every day",
        ],
        action: {
          text: "Questions? Reply and it goes to Priya, your account manager.",
          button: "Open your dashboard",
          tone: "ink",
        },
        footer: "Brightpath Media · Oakville, Ontario · reports@brightpath.ca",
      },
    ],
  },
} satisfies Record<string, { title: string; lead: string; emails: EmailSpec[] }>;

export const EMAIL_VIEWS = Object.keys(EMAIL_SETS) as (keyof typeof EMAIL_SETS)[];
