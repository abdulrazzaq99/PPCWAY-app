"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Chip, PwCard } from "@/components/pw/shell";

/*
  The people in a business, and what each may do. The handoff does not design
  this screen — it says to use the shell and the tokens — so it is built plainly
  from them.

  What a role means is written on the screen rather than left to the word. "Can
  approve changes" is checkable by somebody who has never read the requirements.
*/
export type Person = {
  account_id: string;
  email: string;
  name: string;
  role: string;
  is_you: boolean;
};

export type Org = {
  id: string;
  name: string;
  plan: string;
  currency: string;
  your_role: string;
  can: string[];
  people: Person[];
};

const ROLES: { value: string; label: string; what: string }[] = [
  { value: "owner", label: "Owner", what: "Everything, including billing and disconnecting" },
  { value: "admin", label: "Admin", what: "Approve and make changes, invite people; no billing" },
  { value: "member", label: "Member", what: "See everything and suggest changes; cannot approve" },
  { value: "expert", label: "Expert", what: "Signs off risky changes and logs hours" },
  {
    value: "client_viewer",
    label: "Client viewer",
    what: "Sees their own results and nothing else",
  },
];

function label(role: string): string {
  return ROLES.find((r) => r.value === role)?.label ?? role;
}

export function Team({ org }: { org: Org }) {
  const router = useRouter();
  const [name, setName] = useState(org.name);
  const [naming, setNaming] = useState(false);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("member");
  const [link, setLink] = useState("");
  const [posted, setPosted] = useState(false);
  const [trouble, setTrouble] = useState("");
  const [busy, setBusy] = useState(false);
  const mayInvite = org.can.includes("invite");

  async function send() {
    setBusy(true);
    setTrouble("");
    setLink("");
    try {
      const res = await fetch("/api/org/invite", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ email, role }),
      });
      const said = (await res.json().catch(() => ({}))) as {
        token?: string;
        link?: string;
        emailed?: boolean;
        error?: string;
      };
      if (!res.ok || !said.token) {
        setTrouble(said.error ?? "That invitation could not be made.");
        return;
      }
      setPosted(Boolean(said.emailed));
      setLink(said.link ?? `${window.location.origin}/invite?token=${said.token}`);
      setEmail("");
      router.refresh();
    } catch {
      setTrouble("We could not reach the service.");
    } finally {
      setBusy(false);
    }
  }

  async function changeRole(person: Person, next: string) {
    await fetch("/api/org/role", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ account_id: person.account_id, role: next }),
    });
    router.refresh();
  }

  async function take(person: Person) {
    await fetch(`/api/org/role?account_id=${encodeURIComponent(person.account_id)}`, {
      method: "DELETE",
    });
    router.refresh();
  }

  async function rename() {
    setNaming(true);
    try {
      await fetch("/api/org/name", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ name }),
      });
      router.refresh();
    } finally {
      setNaming(false);
    }
  }

  return (
    <>
      {mayInvite ? (
        <PwCard className="p-5 sm:p-6">
          <h2 className="text-[17px] leading-[22px] font-semibold">What this business is called</h2>
          <p className="text-pw-ink-500 mt-1 text-[14px] leading-[21px]">
            It appears on invitations, on reports, and at the top of every screen your colleagues
            see.
          </p>
          <div className="mt-4 flex flex-wrap items-end gap-3">
            <label className="flex min-w-[260px] flex-1 flex-col gap-[6px]">
              <span className="sr-only">Business name</span>
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="border-pw-border-input bg-pw-card h-[44px] rounded-[12px] border px-3 text-[15px]"
              />
            </label>
            <button
              type="button"
              onClick={rename}
              disabled={naming || !name.trim() || name.trim() === org.name}
              className="bg-pw-blue hover:bg-pw-blue-hover h-[44px] rounded-[12px] px-4 text-[15px] font-semibold text-white disabled:opacity-60"
            >
              {naming ? "Saving…" : "Save"}
            </button>
          </div>
        </PwCard>
      ) : null}

      <PwCard className="overflow-hidden">
        <div className="border-pw-divider border-b px-5 py-5 sm:px-6">
          <h2 className="text-[17px] leading-[22px] font-semibold">People</h2>
          <p className="text-pw-ink-500 mt-1 text-[14px]">
            You are {label(org.your_role).toLowerCase()} of {org.name}.
          </p>
        </div>
        <ul className="divide-pw-divider divide-y">
          {org.people.map((person) => (
            <li
              key={person.account_id}
              className="flex flex-wrap items-center justify-between gap-3 px-5 py-4 sm:px-6"
            >
              <div className="min-w-0">
                <p className="flex flex-wrap items-center gap-2 text-[15px] font-semibold">
                  {person.name || person.email}
                  {person.is_you ? <Chip tone="info">You</Chip> : null}
                </p>
                <p className="text-pw-ink-400 mt-[2px] text-[13px]">{person.email}</p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                {mayInvite && !person.is_you ? (
                  <>
                    <select
                      value={person.role}
                      onChange={(e) => void changeRole(person, e.target.value)}
                      aria-label={`Role for ${person.email}`}
                      className="border-pw-border-input bg-pw-card h-[34px] rounded-[10px] border px-2 text-[14px]"
                    >
                      {ROLES.map((r) => (
                        <option key={r.value} value={r.value}>
                          {r.label}
                        </option>
                      ))}
                    </select>
                    <button
                      type="button"
                      onClick={() => void take(person)}
                      className="text-pw-bad hover:bg-pw-muted rounded-[10px] px-3 py-[6px] text-[14px] font-semibold"
                    >
                      Remove
                    </button>
                  </>
                ) : (
                  <Chip tone="neutral">{label(person.role)}</Chip>
                )}
              </div>
            </li>
          ))}
        </ul>
      </PwCard>

      {mayInvite ? (
        <PwCard className="p-5 sm:p-6">
          <h2 className="text-[17px] leading-[22px] font-semibold">Invite somebody</h2>
          <div className="mt-4 flex flex-wrap items-end gap-3">
            <label className="flex min-w-[240px] flex-1 flex-col gap-[6px]">
              <span className="text-[14px] font-semibold">Their email</span>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@business.ca"
                className="border-pw-border-input bg-pw-card h-[44px] rounded-[12px] border px-3 text-[15px]"
              />
            </label>
            <label className="flex flex-col gap-[6px]">
              <span className="text-[14px] font-semibold">As</span>
              <select
                value={role}
                onChange={(e) => setRole(e.target.value)}
                className="border-pw-border-input bg-pw-card h-[44px] rounded-[12px] border px-3 text-[15px]"
              >
                {ROLES.filter((r) => r.value !== "owner").map((r) => (
                  <option key={r.value} value={r.value}>
                    {r.label}
                  </option>
                ))}
              </select>
            </label>
            <button
              type="button"
              onClick={send}
              disabled={busy || !email.trim()}
              className="bg-pw-blue hover:bg-pw-blue-hover h-[44px] rounded-[12px] px-4 text-[15px] font-semibold text-white disabled:opacity-60"
            >
              {busy ? "Making the link…" : "Invite"}
            </button>
          </div>

          <p className="text-pw-ink-500 mt-2 text-[13px] leading-[19px]">
            {ROLES.find((r) => r.value === role)?.what}
          </p>

          {trouble ? (
            <p className="text-pw-bad mt-3 text-[14px]" role="alert">
              {trouble}
            </p>
          ) : null}

          {link ? (
            <div className="border-pw-blue-tint bg-pw-blue-tint mt-4 rounded-[12px] border p-4">
              <p className="text-pw-blue-ink text-[14px] leading-[21px] font-semibold">
                {posted
                  ? "Sent. It works once, for that address, for fourteen days."
                  : "Email is not set up yet, so pass this link on yourself. It works once, for that address, for fourteen days."}
              </p>
              <p className="text-pw-ink-700 mt-2 text-[13px] break-all">{link}</p>
            </div>
          ) : null}
        </PwCard>
      ) : null}

      <PwCard className="p-5 sm:p-6">
        <h2 className="text-[17px] leading-[22px] font-semibold">What the roles mean</h2>
        <ul className="divide-pw-divider mt-3 divide-y">
          {ROLES.map((r) => (
            <li key={r.value} className="flex flex-wrap gap-x-4 gap-y-1 py-2">
              <span className="w-[120px] text-[14px] font-semibold">{r.label}</span>
              <span className="text-pw-ink-500 flex-1 text-[14px]">{r.what}</span>
            </li>
          ))}
        </ul>
      </PwCard>
    </>
  );
}
