"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  BOX,
  Choice,
  Counts,
  Ghost,
  Label,
  Primary,
  Ring,
  Trouble,
  fieldBorder,
} from "@/components/audit/funnel/bits";
import { FullReport } from "@/components/audit/funnel/report";
import { cn } from "@/lib/cn";
import {
  GOALS,
  RUNNERS,
  SPENDS,
  cameFrom,
  funnel,
  track,
  type Goal,
  type Progress,
  type Runner,
  type SpendBand,
  type Unlocked,
} from "@/lib/funnel";

/*
  The free audit, in the client's Version D flow.

  Start → goal → scan → score → prove the address → the whole report. The score
  and the counts are shown to anybody; the findings are not here to be hidden,
  they are simply not sent until the code is checked, so there is nothing on
  this page for a curious person to dig out.

  One state machine, two layouts. Below 640px the primary action moves to a bar
  stuck to the bottom of the screen, because a thumb is at the bottom of a phone
  and the card is taller than the screen.
*/
type Step = "start" | "goal" | "scan" | "results" | "verify" | "unlocked";

const EVERY = 2000;

/** Which of the three dots are filled, and what the label above them says. */
function marker(step: Step): { label: string; lit: number } {
  if (step === "start") return { label: "Step 1 of 3", lit: 1 };
  if (step === "goal") return { label: "Step 2 of 3", lit: 2 };
  if (step === "scan") return { label: "Step 3 of 3", lit: 3 };
  return { label: "Your audit", lit: 3 };
}

function firstName(full: string): string {
  return full.trim().split(/\s+/)[0] || "there";
}

/** A domain with a dot and a real ending, however they typed it. */
function tidySite(raw: string): string {
  return raw
    .trim()
    .replace(/^https?:\/\//i, "")
    .replace(/\/.*$/, "");
}

function looksLikeSite(raw: string): boolean {
  return /^[a-z0-9-]+(\.[a-z0-9-]+)*\.[a-z]{2,}$/i.test(tidySite(raw));
}

export function FreeAudit({ opened }: { opened?: Unlocked }) {
  const [step, setStep] = useState<Step>(opened ? "unlocked" : "start");
  const [biz, setBiz] = useState("");
  const [url, setUrl] = useState("");
  const [runner, setRunner] = useState<Runner>("me");
  const [goal, setGoal] = useState<Goal | null>(null);
  const [spend, setSpend] = useState<SpendBand | null>(null);

  const [auditId, setAuditId] = useState("");
  const [seen, setSeen] = useState<Progress | null>(null);

  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [optIn, setOptIn] = useState(false);
  const [code, setCode] = useState("");
  const [report, setReport] = useState<Unlocked | null>(opened ?? null);

  const [bad, setBad] = useState<Record<string, boolean>>({});
  const [trouble, setTrouble] = useState("");
  const [busy, setBusy] = useState(false);
  const [resendSaid, setResendSaid] = useState("Resend code");
  const came = useRef<Record<string, string>>({});

  useEffect(() => {
    came.current = cameFrom();
  }, []);

  /* Poll the run until it finishes. The stages come from the server, so the
     bar moves because work is happening, not because time is passing. */
  useEffect(() => {
    if (step !== "scan" || !auditId) return;
    let stop = false;
    let timer: number | undefined;
    const tick = async () => {
      try {
        const now = await funnel.progress(auditId);
        if (stop) return;
        setSeen(now);
        if (now.status === "done") {
          track("audit_complete", { score: now.summary?.score });
          setStep("results");
          return;
        }
        if (now.status === "failed") {
          setTrouble(now.error ?? "We could not finish checking that website.");
          return;
        }
        timer = window.setTimeout(tick, EVERY);
      } catch (exc) {
        if (!stop) setTrouble(exc instanceof Error ? exc.message : "Something went wrong.");
      }
    };
    tick();
    return () => {
      stop = true;
      if (timer) window.clearTimeout(timer);
    };
  }, [step, auditId]);

  const toGoal = useCallback(() => {
    const missingBiz = !biz.trim();
    const missingUrl = !looksLikeSite(url);
    setBad({ biz: missingBiz, url: missingUrl });
    if (missingBiz && missingUrl) return setTrouble("Enter your business name and website.");
    if (missingBiz) return setTrouble("Enter your business name.");
    if (missingUrl) return setTrouble("Enter your website, for example yourbusiness.com");
    setTrouble("");
    track("audit_start", { runner });
    setStep("goal");
  }, [biz, url, runner]);

  const runAudit = useCallback(async () => {
    if (!goal) return setTrouble("Pick what your ads should bring you.");
    if (!spend) return setTrouble("Pick your monthly ad spend.");
    setTrouble("");
    setBusy(true);
    try {
      const started = await funnel.start({
        business_name: biz.trim(),
        site: tidySite(url),
        runner,
        goal,
        spend_band: spend,
        came_from: came.current,
      });
      track("audit_run", { goal, spend_band: spend });
      setAuditId(started.audit_id);
      setSeen(null);
      setStep("scan");
    } catch (exc) {
      setTrouble(exc instanceof Error ? exc.message : "We could not start that audit.");
    } finally {
      setBusy(false);
    }
  }, [goal, spend, biz, url, runner]);

  const unlock = useCallback(async () => {
    const wrong = {
      name: name.trim().length < 2,
      phone: phone.replace(/\D/g, "").length < 7,
      email: !/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email.trim()),
    };
    setBad(wrong);
    if (wrong.name || wrong.phone || wrong.email) {
      return setTrouble("Check the highlighted fields.");
    }
    setTrouble("");
    setBusy(true);
    try {
      await funnel.lead(auditId, {
        name: name.trim(),
        email: email.trim(),
        phone: phone.trim(),
        tips_opt_in: optIn,
        came_from: came.current,
      });
      track("generate_lead", { goal, spend_band: spend });
      setCode("");
      setStep("verify");
    } catch (exc) {
      setTrouble(exc instanceof Error ? exc.message : "We could not send that code.");
    } finally {
      setBusy(false);
    }
  }, [name, phone, email, optIn, auditId, goal, spend]);

  const verify = useCallback(async () => {
    if (!/^\d{6}$/.test(code)) return setTrouble("Enter the 6-digit code from the email.");
    setTrouble("");
    setBusy(true);
    try {
      const whole = await funnel.verify(auditId, code);
      track("lead_verified", { goal, spend_band: spend });
      setReport(whole);
      setStep("unlocked");
    } catch (exc) {
      setTrouble(exc instanceof Error ? exc.message : "That code did not work.");
    } finally {
      setBusy(false);
    }
  }, [code, auditId, goal, spend]);

  const resend = useCallback(async () => {
    try {
      const said = await funnel.resend(auditId);
      setResendSaid(said.sent ? "New code sent" : `Wait ${said.wait_seconds}s`);
      if (said.sent) setCode("");
    } catch {
      setResendSaid("Could not resend");
    }
  }, [auditId]);

  const restart = useCallback(() => {
    setStep("start");
    setAuditId("");
    setSeen(null);
    setReport(null);
    setCode("");
    setBad({});
    setTrouble("");
  }, []);

  const { label, lit } = marker(step);
  const summary = report ?? seen?.summary ?? null;
  const onPhoneBarStep =
    step === "start" || step === "goal" || step === "results" || step === "verify";
  const barLabel = {
    start: "Continue",
    goal: "Run my free audit",
    results: "Email me a code to unlock",
    verify: "Verify and see my audit",
  }[step as "start" | "goal" | "results" | "verify"];
  const barAction = { start: toGoal, goal: runAudit, results: unlock, verify }[
    step as "start" | "goal" | "results" | "verify"
  ];

  return (
    <>
      <section className="bg-[#15112A] text-white">
        <div className="mx-auto flex max-w-[1000px] flex-col items-center gap-[18px] px-6 pt-10 pb-14 text-center sm:pt-14 sm:pb-18">
          <div
            className={cn(
              "flex flex-col items-center gap-[18px]",
              step !== "start" && step !== "goal" && "hidden sm:flex",
            )}
          >
            <span className="rounded-full bg-[#2C2645] px-3 py-[7px] text-[13.5px] font-semibold text-[#E4E0EE]">
              Free Google Ads audit for stores, software, lead-gen and local businesses
            </span>
            <h1 className="display max-w-[860px] text-[32px] leading-[1.06] font-semibold tracking-[-0.025em] sm:text-[58px] sm:leading-[1.04]">
              See what&apos;s costing you customers on Google.
            </h1>
            <p className="max-w-[680px] text-[16px] leading-[1.5] text-[#C9C4D9] sm:text-[19px]">
              Tell us your business and website. We check your site, tracking and search presence,
              then show your score and the issues worth fixing first.
            </p>
            <div className="flex flex-wrap justify-center gap-x-5 gap-y-2 text-[14px] text-[#E4E0EE] sm:text-[15px]">
              {[
                "Free. No card, no account",
                "We read your public website only",
                "Not advertising yet? See what to fix first",
              ].map((claim) => (
                <span key={claim} className="flex items-center gap-2">
                  <span className="font-bold text-[#86EFAC]">✓</span>
                  {claim}
                </span>
              ))}
            </div>
          </div>

          <div
            id="audit"
            className="mt-[10px] box-border flex w-full max-w-[620px] flex-col gap-[18px] rounded-[24px] bg-white p-5 text-left text-[#15112A] shadow-[0_30px_70px_rgba(0,0,0,0.35)] sm:p-7"
          >
            <div className="flex items-center justify-between gap-3">
              <span className="text-[13.5px] font-bold text-[#6B6680]">{label}</span>
              <div className="flex gap-[6px]" aria-hidden>
                {[1, 2, 3].map((k) => (
                  <span
                    key={k}
                    className={cn(
                      "h-[6px] w-[28px] rounded-full",
                      k <= lit ? "bg-[#2F5BEA]" : "bg-[#E8E5DF]",
                    )}
                  />
                ))}
              </div>
            </div>

            {step === "start" && (
              <div className="flex flex-col gap-4">
                <h2 className="display text-[26px] leading-[1.2] font-semibold">
                  Start your free audit
                </h2>
                <Label htmlFor="biz">
                  Business name
                  <input
                    id="biz"
                    type="text"
                    autoComplete="organization"
                    placeholder="Your business or brand"
                    value={biz}
                    onChange={(e) => {
                      setBiz(e.target.value);
                      setBad((b) => ({ ...b, biz: false }));
                      setTrouble("");
                    }}
                    className={cn(BOX, fieldBorder(bad.biz), "font-normal")}
                  />
                </Label>
                <Label htmlFor="url">
                  Website
                  <span
                    className={cn(
                      "flex h-[50px] items-center gap-1 rounded-[12px] border-2 px-[14px]",
                      fieldBorder(bad.url),
                    )}
                  >
                    <span className="font-medium text-[#8A8599]">https://</span>
                    <input
                      id="url"
                      type="text"
                      inputMode="url"
                      autoComplete="url"
                      placeholder="yourbusiness.com"
                      value={url}
                      onChange={(e) => {
                        setUrl(e.target.value);
                        setBad((b) => ({ ...b, url: false }));
                        setTrouble("");
                      }}
                      className="h-full min-w-0 flex-1 border-0 bg-transparent text-[16.5px] font-normal text-[#15112A] outline-none"
                    />
                  </span>
                </Label>
                <div className="flex flex-col gap-[10px]">
                  <span className="text-[14.5px] font-semibold text-[#3A3550]">
                    Who runs your Google Ads today?
                  </span>
                  <div
                    role="group"
                    aria-label="Who runs your Google Ads"
                    className="grid grid-cols-2 gap-2"
                  >
                    {RUNNERS.map((one) => (
                      <Choice key={one.id} on={runner === one.id} onClick={() => setRunner(one.id)}>
                        {one.label}
                      </Choice>
                    ))}
                  </div>
                </div>
                <Trouble>{trouble}</Trouble>
                <div className="hidden sm:block">
                  <Primary onClick={toGoal}>Continue</Primary>
                </div>
                <span className="flex items-center justify-center gap-2 text-center text-[13px] text-[#4A4560]">
                  Reviewed by Google Ads specialists · results in about a minute
                </span>
              </div>
            )}

            {step === "goal" && (
              <div className="flex flex-col gap-4">
                <h2 className="display text-[26px] leading-[1.2] font-semibold">
                  What should your ads bring you?
                </h2>
                <div role="group" aria-label="Main goal" className="grid gap-[10px] sm:grid-cols-2">
                  {GOALS.map((one) => (
                    <Choice
                      key={one.id}
                      on={goal === one.id}
                      onClick={() => {
                        setGoal(one.id);
                        setTrouble("");
                      }}
                      tall="h-auto py-3"
                      className="flex flex-col items-start gap-1 text-left"
                    >
                      <span className="text-[15.5px] font-bold">{one.title}</span>
                      <span className="text-[13px] leading-[1.4] font-normal text-[#6B6680]">
                        {one.detail}
                      </span>
                    </Choice>
                  ))}
                </div>
                <div className="flex flex-col gap-[10px]">
                  <span className="text-[14.5px] font-semibold text-[#3A3550]">
                    Monthly ad spend
                  </span>
                  <div role="group" aria-label="Monthly ad spend" className="flex flex-wrap gap-2">
                    {SPENDS.map((one) => (
                      <Choice
                        key={one.id}
                        on={spend === one.id}
                        onClick={() => {
                          setSpend(one.id);
                          setTrouble("");
                        }}
                        tall="h-[44px]"
                      >
                        {one.label}
                      </Choice>
                    ))}
                  </div>
                </div>
                <Trouble>{trouble}</Trouble>
                <div className="flex gap-[10px]">
                  <Ghost onClick={() => setStep("start")}>Back</Ghost>
                  <div className="hidden flex-1 sm:block">
                    <Primary onClick={runAudit} busy={busy}>
                      {busy ? "Starting…" : "Run my free audit"}
                    </Primary>
                  </div>
                </div>
              </div>
            )}

            {step === "scan" && (
              <div className="flex flex-col gap-[14px]">
                <h2 className="display text-[24px] leading-[1.2] font-semibold">
                  Auditing {biz.trim() || "your business"}
                </h2>
                <div className="h-2 overflow-hidden rounded-full bg-[#F0EEEA]">
                  <div
                    className="h-full rounded-full bg-[#2F5BEA] transition-[width] duration-500"
                    style={{ width: `${seen?.percent ?? 4}%` }}
                  />
                </div>
                <ul className="flex flex-col">
                  {(seen?.stages ?? []).map((one) => (
                    <li
                      key={one.label}
                      className="flex items-center gap-3 border-t border-[#F3F2EE] py-[10px] first:border-t-0"
                    >
                      <span
                        className={cn(
                          "flex size-[22px] shrink-0 items-center justify-center rounded-full text-[12px] font-bold",
                          one.state === "done" && "bg-[#E9FBF0] text-[#15803D]",
                          one.state === "running" && "bg-[#EEF2FE] text-[#2F5BEA]",
                          one.state === "todo" && "bg-[#F4F2EE] text-[#9A94AD]",
                        )}
                      >
                        {one.state === "done" ? "✓" : one.state === "running" ? "···" : ""}
                      </span>
                      <span
                        className={cn(
                          "text-[15px]",
                          one.state === "todo" ? "text-[#9A94AD]" : "text-[#15112A]",
                        )}
                      >
                        {one.label}
                      </span>
                    </li>
                  ))}
                </ul>
                {trouble && (
                  <div className="flex flex-col gap-3">
                    <Trouble>{trouble}</Trouble>
                    <Primary onClick={runAudit}>Try again</Primary>
                  </div>
                )}
              </div>
            )}

            {(step === "results" || step === "verify" || step === "unlocked") && summary && (
              <div className="flex flex-col gap-4">
                <div className="flex items-center gap-[18px]">
                  <Ring score={summary.score} />
                  <div className="flex min-w-0 flex-col gap-[6px]">
                    <span className="display text-[20px] leading-[1.25] font-semibold">
                      {summary.verdict}
                    </span>
                    <span className="text-[13.5px] text-[#6B6680]">
                      {summary.business} · {summary.goal}
                    </span>
                  </div>
                </div>
                <Counts fix={summary.to_fix} improve={summary.to_improve} good={summary.working} />

                {step === "results" && (
                  <div className="flex flex-col gap-3 border-t border-[#F0EEEA] pt-[14px]">
                    <strong className="text-[16px]">
                      Unlock your full report: the fixes, how to do them
                      {spend && spend !== "none" ? " and your wasted spend" : ""}
                    </strong>
                    <div className="grid gap-[10px] sm:grid-cols-2">
                      <Label htmlFor="who" className="text-[14px]">
                        Your name
                        <input
                          id="who"
                          type="text"
                          autoComplete="name"
                          placeholder="First and last name"
                          value={name}
                          onChange={(e) => {
                            setName(e.target.value);
                            setBad((b) => ({ ...b, name: false }));
                            setTrouble("");
                          }}
                          className={cn(BOX, fieldBorder(bad.name), "font-normal")}
                        />
                      </Label>
                      <Label htmlFor="tel" className="text-[14px]">
                        Phone
                        <input
                          id="tel"
                          type="tel"
                          autoComplete="tel"
                          placeholder="+1 416 555 0123"
                          value={phone}
                          onChange={(e) => {
                            setPhone(e.target.value);
                            setBad((b) => ({ ...b, phone: false }));
                            setTrouble("");
                          }}
                          className={cn(BOX, fieldBorder(bad.phone), "font-normal")}
                        />
                      </Label>
                    </div>
                    <Label htmlFor="mail" className="text-[14px]">
                      Work email
                      <input
                        id="mail"
                        type="email"
                        autoComplete="email"
                        placeholder="you@company.com"
                        value={email}
                        onChange={(e) => {
                          setEmail(e.target.value);
                          setBad((b) => ({ ...b, email: false }));
                          setTrouble("");
                        }}
                        className={cn(BOX, fieldBorder(bad.email), "font-normal")}
                      />
                    </Label>
                    <Trouble>{trouble}</Trouble>
                    <label className="flex cursor-pointer items-start gap-[10px] text-[13px] leading-[1.45] text-[#4A4560]">
                      <input
                        type="checkbox"
                        checked={optIn}
                        onChange={(e) => setOptIn(e.target.checked)}
                        className="mt-[2px] size-5 shrink-0 accent-[#2F5BEA]"
                      />
                      Also send me Google Ads tips and offers. Optional, unsubscribe any time.
                    </label>
                    <div className="hidden sm:block">
                      <Primary onClick={unlock} busy={busy} tall={54}>
                        {busy ? "Sending…" : "Email me a code to unlock"}
                      </Primary>
                    </div>
                    <span className="text-center text-[12.5px] leading-[1.45] text-[#6B6680]">
                      We&apos;ll send a 6-digit code to confirm your email, then show your full
                      audit. A specialist may call to walk you through it. We never sell your
                      details. <a href="/privacy">Privacy</a>
                    </span>
                  </div>
                )}

                {step === "verify" && (
                  <div className="flex flex-col gap-3 border-t border-[#F0EEEA] pt-[14px]">
                    <div className="flex items-center gap-3">
                      <span className="flex size-[44px] shrink-0 items-center justify-center rounded-[12px] bg-[#EEF2FE] text-[#2F5BEA]">
                        ✉
                      </span>
                      <div className="flex flex-col gap-[2px]">
                        <strong className="text-[17px]">Check your email to see your audit</strong>
                        <span className="text-[14px] text-[#4A4560]">
                          We sent a 6-digit code to <strong>{email}</strong>
                        </span>
                      </div>
                    </div>
                    <Label htmlFor="code" className="text-[14px]">
                      Verification code
                      <input
                        id="code"
                        type="text"
                        inputMode="numeric"
                        autoComplete="one-time-code"
                        maxLength={6}
                        placeholder="••••••"
                        value={code}
                        onChange={(e) => {
                          setCode(e.target.value.replace(/\D/g, "").slice(0, 6));
                          setTrouble("");
                        }}
                        className="h-[60px] w-full rounded-[12px] border-2 border-[#D9DEF0] px-4 text-center text-[28px] font-semibold tracking-[0.4em] text-[#15112A] outline-none focus:border-[#2F5BEA]"
                      />
                    </Label>
                    <Trouble>{trouble}</Trouble>
                    <div className="hidden sm:block">
                      <Primary onClick={verify} busy={busy} tall={54}>
                        {busy ? "Checking…" : "Verify and see my audit"}
                      </Primary>
                    </div>
                    <span className="text-center text-[13.5px] leading-[1.5] text-[#4A4560]">
                      Or tap the link in the email. It opens your audit on any device.
                    </span>
                    <div className="flex flex-wrap justify-center gap-x-[18px] gap-y-[6px] text-[14px]">
                      <button
                        type="button"
                        onClick={resend}
                        className="px-1 py-[6px] font-semibold text-[#2F5BEA]"
                      >
                        {resendSaid}
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          setStep("results");
                          setCode("");
                          setTrouble("");
                        }}
                        className="px-1 py-[6px] font-semibold text-[#2F5BEA]"
                      >
                        Change email
                      </button>
                    </div>
                    <span className="text-center text-[12.5px] text-[#6B6680]">
                      Can&apos;t find it? Check spam or promotions. The code expires in 15 minutes.
                    </span>
                  </div>
                )}

                {step === "unlocked" && report && (
                  <div className="flex flex-col gap-3 border-t border-[#F0EEEA] pt-[14px]">
                    <div className="rounded-[12px] bg-[#E9FBF0] px-[14px] py-3 text-[14.5px] leading-[1.5] text-[#14532D]">
                      <strong>Email verified. Thanks, {firstName(name || report.business)}.</strong>{" "}
                      Your full report is open below, and a copy is in your inbox.
                    </div>
                    <a
                      href="#report"
                      className="flex h-[54px] items-center justify-center rounded-[14px] bg-[#2F5BEA] text-[17px] font-semibold text-white hover:brightness-95"
                    >
                      See my full report
                    </a>
                  </div>
                )}

                <button
                  type="button"
                  onClick={restart}
                  className="self-center rounded-[10px] px-3 py-2 text-[14px] font-semibold text-[#6B6680] hover:bg-[#F3F2EE]"
                >
                  Run another audit
                </button>
              </div>
            )}
          </div>
        </div>
      </section>

      {report && <FullReport report={report} who={firstName(name || report.business)} />}

      {/* On a phone the action lives where the thumb is. Not while the audit
          is running, and not once there is nothing left to do. */}
      {onPhoneBarStep && (
        <div
          className="fixed inset-x-0 bottom-0 z-40 border-t border-[#E8E5DF] bg-white px-4 pt-3 sm:hidden"
          style={{ paddingBottom: "max(16px, env(safe-area-inset-bottom))" }}
        >
          <Primary onClick={barAction} busy={busy} tall={54}>
            {busy ? "Working…" : barLabel}
          </Primary>
        </div>
      )}
      {onPhoneBarStep && <div className="h-[88px] sm:hidden" aria-hidden />}
    </>
  );
}
