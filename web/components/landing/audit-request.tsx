"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { CheckCircle } from "@phosphor-icons/react";
import { AuthCard, AuthShell } from "@/components/auth/auth-shell";
import { Button, TextLink } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Field, Input } from "@/components/ui/field";

/*
  The free audit request. Six answers, then a thank-you card. The eight checks run
  on the website; the rest is so a person can send the report and follow up.
  Label above each input, the error under it, and nothing is sent until the
  consent box is ticked.
*/
type Values = { name: string; email: string; phone: string; business: string; site: string };
type Errors = Partial<Record<keyof Values | "consent", string>>;

const EMPTY: Values = { name: "", email: "", phone: "", business: "", site: "" };

function validate(v: Values, consent: boolean): Errors {
  const e: Errors = {};
  if (!v.name.trim()) e.name = "Type your name.";
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v.email.trim()))
    e.email = "Type an email address we can send the report to.";
  if (v.phone.replace(/\D/g, "").length < 10) e.phone = "Type a phone number with the area code.";
  if (!v.business.trim()) e.business = "Type the name of your business.";
  const site = v.site.trim().replace(/^https?:\/\//, "");
  if (!/^[a-z0-9-]+(\.[a-z0-9-]+)+(\/.*)?$/i.test(site))
    e.site = "Type your website address, like alphaplumbing.ca";
  if (!consent) e.consent = "Tick the box so we can send you the report.";
  return e;
}

export function AuditRequest() {
  const [values, setValues] = useState<Values>(EMPTY);
  const [consent, setConsent] = useState(false);
  const [errors, setErrors] = useState<Errors>({});
  const [working, setWorking] = useState(false);
  const [sent, setSent] = useState<string | null>(null);
  const [serverError, setServerError] = useState<string | null>(null);

  const set = (key: keyof Values) => (event: React.ChangeEvent<HTMLInputElement>) =>
    setValues((v) => ({ ...v, [key]: event.target.value }));

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const next = validate(values, consent);
    setErrors(next);
    if (Object.keys(next).length) return;
    setWorking(true);
    setServerError(null);
    try {
      const res = await fetch("/api/audit", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          name: values.name.trim(),
          email: values.email.trim(),
          phone: values.phone.trim(),
          business_name: values.business.trim(),
          site: values.site.trim(),
          consent,
          source: "landing",
        }),
      });
      const data = (await res.json().catch(() => ({}))) as {
        id?: string;
        error?: string;
        detail?: unknown;
      };
      if (res.ok && data.id) {
        setSent(data.id);
      } else if (res.status === 422 && Array.isArray(data.detail)) {
        const first = data.detail[0] as { msg?: string };
        setServerError(
          (first?.msg ?? "Check the form and try again.").replace(/^Value error, /, ""),
        );
      } else {
        setServerError(data.error ?? "Something went wrong on our side. Try again in a minute.");
      }
    } catch {
      setServerError("We could not reach the audit service. Check your connection and try again.");
    } finally {
      setWorking(false);
    }
  }

  return (
    <AuthShell
      headline="A free check of your website, the same eight an agency runs."
      body="Tell us where to send it. We look at your site within one working day and reply with what to fix first, in plain words."
      footnote="We change nothing on your site, and we never share what you tell us."
      below={
        sent ? null : (
          <>
            Already with PPCWay? <TextLink href="/login">Sign in</TextLink>
          </>
        )
      }
    >
      {sent ? (
        <AuthCard
          title="Thanks, we have it."
          intro={`The report goes to ${values.email.trim()} within one working day.`}
        >
          <div className="bg-brand-tint text-ink flex items-start gap-3 rounded-[12px] p-4 text-[14px] leading-5">
            <CheckCircle
              size={22}
              weight="fill"
              className="text-brand mt-[-1px] shrink-0"
              aria-hidden
            />
            <span>
              We will check {values.site.trim().replace(/^https?:\/\//, "")} for{" "}
              {values.business.trim()} and call {values.phone.trim()} only if something in the
              report needs a word from you.
            </span>
          </div>
          <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
            <Link
              href={`/audit/${sent}`}
              className="text-brand text-[14px] leading-[17px] font-semibold"
            >
              Watch the checks run
            </Link>
            <Link href="/" className="text-muted text-[14px] leading-[17px] font-semibold">
              Back to the home page
            </Link>
          </div>
        </AuthCard>
      ) : (
        <AuthCard
          title="Get a free audit"
          intro="Six answers. The report comes to your email within one working day."
          onSubmit={submit}
        >
          <Field label="Your name" error={errors.name}>
            {(id) => (
              <Input
                id={id}
                autoComplete="name"
                placeholder="Daniel Walsh"
                value={values.name}
                onChange={set("name")}
                invalid={Boolean(errors.name)}
              />
            )}
          </Field>
          <Field label="Email" error={errors.email}>
            {(id) => (
              <Input
                id={id}
                type="email"
                inputMode="email"
                autoComplete="email"
                placeholder="daniel@alphaplumbing.ca"
                value={values.email}
                onChange={set("email")}
                invalid={Boolean(errors.email)}
              />
            )}
          </Field>
          <Field label="Phone" error={errors.phone}>
            {(id) => (
              <Input
                id={id}
                type="tel"
                inputMode="tel"
                autoComplete="tel"
                placeholder="(905) 555 0142"
                value={values.phone}
                onChange={set("phone")}
                invalid={Boolean(errors.phone)}
              />
            )}
          </Field>
          <Field label="Business name" error={errors.business}>
            {(id) => (
              <Input
                id={id}
                autoComplete="organization"
                placeholder="Alpha Plumbing"
                value={values.business}
                onChange={set("business")}
                invalid={Boolean(errors.business)}
              />
            )}
          </Field>
          <Field
            label="Website"
            error={errors.site}
            hint={errors.site ? undefined : "The page your ads would send people to."}
          >
            {(id) => (
              <Input
                id={id}
                inputMode="url"
                autoComplete="url"
                placeholder="alphaplumbing.ca"
                value={values.site}
                onChange={set("site")}
                invalid={Boolean(errors.site)}
              />
            )}
          </Field>
          <div className="flex flex-col gap-2">
            <Checkbox checked={consent} onChange={setConsent}>
              PPCWay may email and call me about this audit. No newsletters, and I can ask you to
              stop at any time. PPCWay reads my website to write the report and may send what it
              says to its AI provider, Anthropic.
            </Checkbox>
            {errors.consent ? (
              <p className="text-meta font-medium text-[#c0392b]" role="alert">
                {errors.consent}
              </p>
            ) : null}
          </div>
          {serverError ? (
            <p className="text-meta font-medium text-[#c0392b]" role="alert">
              {serverError}
            </p>
          ) : null}
          <Button type="submit" full working={working ? "Sending" : false}>
            Send me the free audit
          </Button>
        </AuthCard>
      )}
    </AuthShell>
  );
}
