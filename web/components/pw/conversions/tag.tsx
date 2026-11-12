"use client";

import { CheckIcon, CopyIcon, EnvelopeSimpleIcon } from "@phosphor-icons/react";
import { useId, useRef, useState, type ReactNode } from "react";
import { Choice, Labelled, Note } from "@/components/pw/create/kit";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/field";
import { cn } from "@/lib/cn";
import { domainOf, said, talk, type Action, type Snippet, type Tag } from "./types";

/*
  The Google tag, the way Google's Conversions summary hands it over: the tag
  for every page, an event snippet per website action, and the other ways to
  install it (Google Tag Manager, or by email to whoever looks after the
  site). Then "Check the tag", which reads the page for it.

  PPCWay cannot watch the tag fire the way Google does, so the check reads the
  page's own markup. A tag added through Tag Manager is not in that markup,
  and the sentence says so instead of saying it is missing.
*/

/** A block of code with a Copy button. */
export function CodeBox({ code, label }: { code: string; label: string }) {
  const [copied, setCopied] = useState(false);
  const box = useRef<HTMLPreElement>(null);
  async function copy() {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // No clipboard (an older browser, or a page not in focus): select the
      // code so a keyboard copy takes it.
      const range = document.createRange();
      if (box.current) {
        range.selectNodeContents(box.current);
        const picked = window.getSelection();
        picked?.removeAllRanges();
        picked?.addRange(range);
      }
    }
  }
  return (
    <div className="border-pw-border bg-pw-muted min-w-0 overflow-hidden rounded-[12px] border">
      <div className="border-pw-border flex items-center justify-between gap-3 border-b px-4 py-2">
        <span className="text-pw-ink-500 min-w-0 truncate text-[12px] font-semibold">{label}</span>
        <button
          type="button"
          onClick={copy}
          className="text-pw-blue hover:text-pw-blue-hover inline-flex shrink-0 items-center gap-1 text-[13px] font-semibold"
        >
          {copied ? <CheckIcon className="size-4" /> : <CopyIcon className="size-4" />}
          <span aria-live="polite">{copied ? "Copied" : "Copy"}</span>
        </button>
      </div>
      <pre
        ref={box}
        className="text-pw-ink-700 max-h-[280px] overflow-auto px-4 py-3 font-mono text-[12px] leading-[18px] whitespace-pre"
      >
        <code>{code}</code>
      </pre>
    </div>
  );
}

/** A short value with its own Copy button, for the Tag Manager fields. */
function CopyValue({ value, label }: { value: string; label: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <span className="inline-flex items-center gap-2">
      <code className="bg-pw-muted text-pw-ink rounded-[6px] px-2 py-[2px] text-[13px]">
        {value || "Not given"}
      </code>
      {value ? (
        <button
          type="button"
          aria-label={`Copy ${label}`}
          onClick={async () => {
            try {
              await navigator.clipboard.writeText(value);
              setCopied(true);
              setTimeout(() => setCopied(false), 2000);
            } catch {
              setCopied(false);
            }
          }}
          className="text-pw-blue hover:text-pw-blue-hover"
        >
          {copied ? <CheckIcon className="size-4" /> : <CopyIcon className="size-4" />}
        </button>
      ) : null}
    </span>
  );
}

/** What the page's markup says about the tag, in a sentence. */
export function tagSentence(
  tag: Tag,
  site: string,
  trackingId: string,
): { tone: "good" | "warn" | "bad" | "info"; words: string } {
  const where = domainOf(site);
  const managerToo = tag.tag_manager
    ? " Google Tag Manager is there too, and a tag added through Tag Manager does not show in the page source, so it may be there after all."
    : "";
  if (!site) {
    return {
      tone: "info",
      words: "PPCWay does not know your website yet, so it cannot look for the tag.",
    };
  }
  if (!tag.read) {
    return {
      tone: "warn",
      words: `PPCWay could not read ${where}, so it cannot say whether the Google tag is there.`,
    };
  }
  if (tag.this_account) {
    return {
      tone: "good",
      words: `The Google tag for this account, ${trackingId}, is on ${where}.`,
    };
  }
  if (tag.google_tag) {
    const ids = tag.found_ids.length ? ` PPCWay found ${tag.found_ids.join(", ")}.` : "";
    return {
      tone: "warn",
      words: trackingId
        ? `A Google tag is on ${where}, but not this account's ${trackingId}.${ids}${managerToo}`
        : `A Google tag is on ${where}. This account has no tag ID yet; Google makes one with its first conversion action.${ids}`,
    };
  }
  if (tag.tag_manager) {
    return {
      tone: "info",
      words: `Google Tag Manager is on ${where}. A tag added through Tag Manager does not show in the page source, so PPCWay cannot see it from here. Use Tag Manager's Preview to check it.`,
    };
  }
  return {
    tone: "bad",
    words: `The Google tag is not on ${where} yet. Website conversions are not counted until it is.`,
  };
}

/** "Check the tag": reads the page again and says what it found. */
export function TagCheck({
  site,
  trackingId,
  initial,
  label = "Check the tag",
  children,
}: {
  site: string;
  trackingId: string;
  initial?: Tag;
  label?: string;
  /** Other buttons, shown beside this one. */
  children?: ReactNode;
}) {
  const [tag, setTag] = useState<Tag | undefined>(initial);
  const [busy, setBusy] = useState(false);
  const [trouble, setTrouble] = useState("");
  const [checked, setChecked] = useState(false);

  async function check() {
    setBusy(true);
    setTrouble("");
    const { ok, data } = await talk<Tag>(
      `tag?url=${encodeURIComponent(site)}&tracking=${encodeURIComponent(trackingId)}`,
    );
    setBusy(false);
    if (!ok) {
      setTrouble(said(data, "PPCWay could not look at your site just now."));
      return;
    }
    setTag(data);
    setChecked(true);
  }

  const sentence = tag ? tagSentence(tag, site, trackingId) : null;
  return (
    <div className="flex flex-col gap-3">
      {sentence ? (
        <Note tone={sentence.tone}>
          <span aria-live="polite">
            {checked ? "Checked just now. " : ""}
            {sentence.words}
          </span>
        </Note>
      ) : null}
      {trouble ? <p className="text-pw-bad text-[13px]">{trouble}</p> : null}
      <div className="flex flex-wrap items-center gap-3">
        <Button
          variant="secondary"
          size="sm"
          onClick={check}
          disabled={!site}
          working={busy ? "Checking…" : false}
        >
          {label}
        </Button>
        {children}
      </div>
      {!site ? (
        <p className="text-pw-ink-500 text-[13px]">
          PPCWay needs your website&apos;s address to check it.
        </p>
      ) : null}
    </div>
  );
}

const html = (s: Snippet) => !s.page_format || s.page_format === "HTML";

function snippetOf(a: Action, type: string): Snippet | undefined {
  return a.snippets.find((s) => s.type === type && html(s) && s.event_snippet);
}

/** The Conversion ID (digits only, as Tag Manager asks) and label in a snippet. */
export function idAndLabel(snippet: string): { id: string; label: string } {
  const found = snippet.match(/['"]AW-(\d+)\/([A-Za-z0-9_-]+)['"]/);
  return found ? { id: found[1], label: found[2] } : { id: "", label: "" };
}

type Way = "self" | "gtm" | "email";
const WAYS: { id: Way; label: string }[] = [
  { id: "self", label: "Install the tag yourself" },
  { id: "gtm", label: "Use Google Tag Manager" },
  { id: "email", label: "Email the instructions" },
];

function Step({ n, title, children }: { n: number; title: string; children: ReactNode }) {
  return (
    <li className="flex min-w-0 gap-3">
      <span className="bg-pw-blue-tint text-pw-blue-ink flex size-6 shrink-0 items-center justify-center rounded-full text-[12px] font-bold">
        {n}
      </span>
      <div className="flex min-w-0 flex-1 flex-col gap-3">
        <p className="text-pw-ink text-[14px] leading-[20px] font-semibold">{title}</p>
        {children}
      </div>
    </li>
  );
}

const Code = ({ children }: { children: ReactNode }) => (
  <code className="bg-pw-muted text-pw-ink rounded-[6px] px-1 py-[1px] text-[12px]">
    {children}
  </code>
);

/** One website action's event snippet, by page load or by click, as Google offers both. */
function EventSnippet({ action }: { action: Action }) {
  const load = snippetOf(action, "WEBPAGE");
  const click = snippetOf(action, "WEBPAGE_ONCLICK");
  const [by, setBy] = useState<"load" | "click">(load ? "load" : "click");
  const name = useId();
  const shown = by === "load" ? load : click;
  if (!load && !click) {
    return (
      <p className="text-pw-ink-500 text-[13px]">
        Google has not sent this action&apos;s snippet yet. It shows on the Conversions summary once
        Google has it.
      </p>
    );
  }
  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-col gap-2 sm:flex-row sm:gap-6">
        {load ? (
          <Choice name={name} checked={by === "load"} onChange={() => setBy("load")}>
            Page load
          </Choice>
        ) : null}
        {click ? (
          <Choice name={name} checked={by === "click"} onChange={() => setBy("click")}>
            Click
          </Choice>
        ) : null}
      </div>
      <p className="text-pw-ink-600 text-[13px] leading-[19px]">
        {by === "load" ? (
          <>
            Paste it in the <Code>&lt;head&gt;</Code> of the page people reach after converting,
            like your thank-you or order confirmation page, right after the Google tag. A conversion
            counts each time that page loads.
          </>
        ) : (
          <>
            Paste it in the <Code>&lt;head&gt;</Code> of the page with the button or link, right
            after the Google tag. Then add{" "}
            <Code>onclick=&quot;return gtag_report_conversion(&apos;https://…&apos;)&quot;</Code> to
            the button or link, with the address it opens. A conversion counts on each click.
          </>
        )}
        {!action.value.always
          ? " The snippet sends the default value: put each conversion's real value in it, and the order number as the transaction ID, so each one reports what it was worth."
          : ""}
      </p>
      {shown ? (
        <CodeBox code={shown.event_snippet} label={`Event snippet for ${action.name}`} />
      ) : null}
    </div>
  );
}

/** The email body: the same instructions, in plain text. */
function emailBody(
  account: string,
  site: string,
  globalTag: string,
  web: Action[],
  calls: Action[],
): string {
  const lines = [
    "Hello,",
    "",
    `Please add the Google Ads tag${account ? ` for ${account}` : ""} to ${domainOf(site) || "our website"}.`,
    "",
    "1. Paste this Google tag into the code of every page, right after the <head> tag, once per page:",
    "",
    globalTag,
  ];
  let n = 2;
  for (const a of web) {
    const s = snippetOf(a, "WEBPAGE") ?? snippetOf(a, "WEBPAGE_ONCLICK");
    if (!s) continue;
    lines.push(
      "",
      `${n}. "${a.name}": paste this on the page people reach after converting (like the thank-you page), right after the Google tag:`,
      "",
      s.event_snippet,
    );
    n += 1;
  }
  for (const a of calls) {
    const s = snippetOf(a, "WEBSITE_CALL");
    if (!s) continue;
    lines.push(
      "",
      `${n}. "${a.name}": paste this on every page that shows our phone number, right after the Google tag, and put our number in it exactly as it is written on the page:`,
      "",
      s.event_snippet,
    );
    n += 1;
  }
  lines.push("", "Thank you.");
  return lines.join("\n");
}

export function TagSetup({
  globalTag,
  trackingId,
  actions,
  site,
  account,
}: {
  globalTag: string;
  trackingId: string;
  /** The account's actions; only website and website-call ones are used. */
  actions: Action[];
  site: string;
  account: string;
}) {
  const [way, setWay] = useState<Way>("self");
  const [to, setTo] = useState("");
  const [copied, setCopied] = useState(false);
  const web = actions.filter((a) => a.type === "WEBPAGE");
  const calls = actions.filter((a) => a.type === "WEBSITE_CALL");

  if (!globalTag) {
    return (
      <Note tone="info">
        Google has not sent the tag yet. It comes with the account&apos;s first website conversion
        action: create one, and the tag shows here.
      </Note>
    );
  }

  const body = emailBody(account, site, globalTag, web, calls);
  const mailto = `mailto:${encodeURIComponent(to.trim())}?subject=${encodeURIComponent(
    "The Google Ads tag for our website",
  )}&body=${encodeURIComponent(body)}`;

  return (
    <div className="flex flex-col gap-5">
      <div
        role="radiogroup"
        aria-label="How to install the tag"
        className="bg-pw-muted flex flex-col gap-1 rounded-[12px] p-1 sm:flex-row"
      >
        {WAYS.map((w) => (
          <button
            key={w.id}
            type="button"
            role="radio"
            aria-checked={way === w.id}
            onClick={() => setWay(w.id)}
            className={cn(
              "rounded-[9px] px-3 py-[8px] text-left text-[14px] font-semibold sm:flex-1 sm:text-center",
              way === w.id
                ? "bg-pw-card text-pw-ink shadow-sm"
                : "text-pw-ink-500 hover:text-pw-ink",
            )}
          >
            {w.label}
          </button>
        ))}
      </div>

      {way === "self" ? (
        <ol className="flex flex-col gap-6">
          <Step n={1} title="Paste the Google tag on every page">
            <p className="text-pw-ink-600 text-[13px] leading-[19px]">
              Copy the tag and paste it into the code of every page of your website, right after the{" "}
              <Code>&lt;head&gt;</Code> tag, once per page. If your website builder has a box for a
              Google tag or Google Ads ID, give it <Code>{trackingId || "your tag ID"}</Code>{" "}
              instead.
            </p>
            <CodeBox code={globalTag} label="Google tag" />
          </Step>
          {web.map((a, i) => (
            <Step key={a.resource} n={i + 2} title={`Add the event snippet for "${a.name}"`}>
              <EventSnippet action={a} />
            </Step>
          ))}
          {calls.map((a, i) => {
            const s = snippetOf(a, "WEBSITE_CALL");
            return (
              <Step key={a.resource} n={web.length + i + 2} title={`Track calls from your website`}>
                <p className="text-pw-ink-600 text-[13px] leading-[19px]">
                  For &quot;{a.name}&quot;: paste this on every page that shows your phone number,
                  right after the Google tag, and put your number in it exactly as it is written on
                  the page. Google then shows a forwarding number to people who came from an ad, and
                  counts their calls.
                </p>
                {s ? (
                  <CodeBox code={s.event_snippet} label={`Phone snippet for ${a.name}`} />
                ) : (
                  <p className="text-pw-ink-500 text-[13px]">
                    Google has not sent this snippet yet.
                  </p>
                )}
              </Step>
            );
          })}
        </ol>
      ) : null}

      {way === "gtm" ? (
        <div className="flex flex-col gap-4">
          <ol className="text-pw-ink-600 flex list-decimal flex-col gap-2 pl-5 text-[14px] leading-[20px]">
            <li>In Tag Manager, open the container on your website and choose New tag.</li>
            <li>Choose Tag configuration, then Google Ads, then Google Ads Conversion Tracking.</li>
            <li>Enter the Conversion ID and Conversion label below for the action.</li>
            <li>
              Under Triggering, choose when it counts: the confirmation page loading, or the click.
            </li>
            <li>If the container has no Conversion Linker tag, add one that fires on all pages.</li>
            <li>Save, then Submit to publish the container.</li>
          </ol>
          {web.length || calls.length ? (
            <ul className="border-pw-border divide-pw-border divide-y rounded-[12px] border">
              {[...web, ...calls].map((a) => {
                const s =
                  snippetOf(a, "WEBPAGE") ??
                  snippetOf(a, "WEBPAGE_ONCLICK") ??
                  snippetOf(a, "WEBSITE_CALL");
                const { id, label } = idAndLabel(s?.event_snippet ?? "");
                return (
                  <li key={a.resource} className="flex flex-col gap-2 px-4 py-3">
                    <p className="text-pw-ink text-[14px] font-semibold">{a.name}</p>
                    <div className="flex flex-col gap-2 text-[13px] sm:flex-row sm:gap-6">
                      <span className="text-pw-ink-500">
                        Conversion ID <CopyValue value={id} label="Conversion ID" />
                      </span>
                      <span className="text-pw-ink-500">
                        Conversion label <CopyValue value={label} label="Conversion label" />
                      </span>
                    </div>
                    {a.type === "WEBSITE_CALL" ? (
                      <p className="text-pw-ink-500 text-[13px]">
                        For calls from your website, choose Google Ads Calls from Website Conversion
                        instead, with the same ID and label and your number as written on the page.
                      </p>
                    ) : null}
                  </li>
                );
              })}
            </ul>
          ) : null}
          <Note tone="info">
            A tag added through Tag Manager does not show in your page&apos;s source, so
            PPCWay&apos;s check cannot see it. Use Tag Manager&apos;s Preview to test it.
          </Note>
        </div>
      ) : null}

      {way === "email" ? (
        <div className="flex flex-col gap-4">
          <p className="text-pw-ink-600 text-[14px] leading-[20px]">
            Send the tag and the instructions to whoever looks after your website. Your mail app
            opens with everything written out.
          </p>
          <Labelled label="Their email address" className="max-w-[420px]">
            <Input
              type="email"
              value={to}
              onChange={(e) => setTo(e.target.value)}
              placeholder="developer@example.com"
              aria-label="Their email address"
            />
          </Labelled>
          <div className="flex flex-wrap items-center gap-3">
            <a
              href={mailto}
              className="bg-pw-blue hover:bg-pw-blue-hover inline-flex h-11 items-center gap-2 rounded-[12px] px-5 text-[14px] font-semibold text-white sm:h-[38px]"
            >
              <EnvelopeSimpleIcon className="size-4" /> Write the email
            </a>
            <Button
              variant="secondary"
              size="sm"
              onClick={async () => {
                try {
                  await navigator.clipboard.writeText(body);
                  setCopied(true);
                  setTimeout(() => setCopied(false), 2000);
                } catch {
                  setCopied(false);
                }
              }}
            >
              {copied ? "Copied" : "Copy the email text"}
            </Button>
          </div>
          <p className="text-pw-ink-500 text-[13px]">
            Some mail apps cut a long message short. If the code is missing, copy the email text
            instead and paste it in.
          </p>
        </div>
      ) : null}
    </div>
  );
}
