"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Field, Input } from "@/components/ui/field";

/*
  The "We could not find you" form: business name, what you do, where you work, and a
  website if there is one. With a website it starts a real audit and goes to the live
  checking page; without one it explains what happens next.
*/
export function ManualForm() {
  const router = useRouter();
  const [values, setValues] = useState({
    business: "Alpha Plumbing",
    trade: "Plumbing",
    where: "Mississauga, Ontario",
    site: "",
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [working, setWorking] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);
  const set = (k: keyof typeof values) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setValues((v) => ({ ...v, [k]: e.target.value }));

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const next: Record<string, string> = {};
    if (!values.business.trim()) next.business = "Type the name of your business.";
    if (!values.where.trim()) next.where = "Type the town you work in.";
    const site = values.site.trim().replace(/^https?:\/\//, "");
    if (site && !/^[a-z0-9-]+(\.[a-z0-9-]+)+(\/.*)?$/i.test(site))
      next.site = "Type your website address, like alphaplumbing.ca";
    setErrors(next);
    if (Object.keys(next).length) return;
    if (!site) {
      setServerError(
        "Without a website we start from your Google listing, which is not connected yet. Add the site address for now.",
      );
      return;
    }
    setWorking(true);
    setServerError(null);
    try {
      const res = await fetch("/api/audit", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          business_name: values.business.trim(),
          trade: values.trade.trim(),
          city: values.where.trim(),
          site,
          source: "landing",
        }),
      });
      const data = (await res.json().catch(() => ({}))) as { id?: string; error?: string };
      if (res.ok && data.id) router.push(`/audit/${data.id}`);
      else setServerError(data.error ?? "Something went wrong on our side. Try again in a minute.");
    } catch {
      setServerError("We could not reach the audit service. Try again in a minute.");
    } finally {
      setWorking(false);
    }
  }

  return (
    <form onSubmit={submit} noValidate className="flex flex-col gap-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Business name" error={errors.business}>
          {(id) => (
            <Input
              id={id}
              value={values.business}
              onChange={set("business")}
              invalid={Boolean(errors.business)}
              autoComplete="organization"
            />
          )}
        </Field>
        <Field label="What you do">
          {(id) => (
            <Input
              id={id}
              value={values.trade}
              onChange={set("trade")}
              trailing={<span className="text-faint text-[14px] font-medium">Change</span>}
            />
          )}
        </Field>
        <Field label="Where you work" error={errors.where}>
          {(id) => (
            <Input
              id={id}
              value={values.where}
              onChange={set("where")}
              invalid={Boolean(errors.where)}
              autoComplete="address-level2"
            />
          )}
        </Field>
        <Field label="Website, if you have one" error={errors.site}>
          {(id) => (
            <Input
              id={id}
              value={values.site}
              onChange={set("site")}
              placeholder="alphaplumbing.ca"
              inputMode="url"
              invalid={Boolean(errors.site)}
            />
          )}
        </Field>
      </div>
      {serverError ? (
        <p className="text-meta font-medium text-[#c0392b]" role="alert">
          {serverError}
        </p>
      ) : null}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-faint text-[14px] leading-[17px]">
          No website is fine. Most trades we work with started without one.
        </p>
        <Button
          type="submit"
          size="sm"
          className="h-[42px] shrink-0"
          working={working ? "Checking" : false}
        >
          Check my business
        </Button>
      </div>
    </form>
  );
}
