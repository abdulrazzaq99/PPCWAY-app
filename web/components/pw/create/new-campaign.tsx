"use client";

import { ArrowRightIcon } from "@phosphor-icons/react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/field";
import { call, said, type Objective, type Setup, type Spec, type SpecDraft } from "@/lib/creation";
import { GoalsTable, ObjectiveTiles, TypeTiles, WaysToReach } from "./goal-parts";
import { Card, Note } from "./kit";

/*
  Google's "New campaign" page, the step every campaign starts on: choose an
  objective (or none), keep or change the conversion goals it brings, choose
  a campaign type, the ways to reach the goal, and a name. "Continue" makes
  the draft; every later step saves into it.
*/

const NO_WAYS: Spec["ways"] = {
  website: true,
  website_url: "",
  calls: false,
  phone_country: "",
  phone_number: "",
  store_visits: false,
  app: false,
  app_id: "",
  app_store: "GOOGLE_APP_STORE",
  lead_forms: false,
};

export function NewCampaign({ setup, website }: { setup: Setup; website: string }) {
  const router = useRouter();
  const [objective, setObjective] = useState<Objective | null>(null);
  const [type, setType] = useState<string | null>(null);
  const [goals, setGoals] = useState<Spec["goals"]>({
    account_default: true,
    chosen: [],
    available: [],
  });
  const [ways, setWays] = useState<Spec["ways"]>({ ...NO_WAYS, website_url: website });
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [trouble, setTrouble] = useState("");

  if (!setup.connected) {
    return (
      <Note tone="warn">
        Connect a Google Ads account first.{" "}
        <Link href="/settings" className="font-semibold underline">
          Go to settings
        </Link>
      </Note>
    );
  }

  const o = objective ? setup.objectives[objective] : null;
  const typeLabel = type ? setup.types[type]?.label : "";
  const ready = Boolean(objective && type && name.trim() && ways.website_url.trim());

  async function start() {
    setBusy(true);
    setTrouble("");
    const available = (setup.conversion?.goals ?? []).map((g) => ({
      category: g.category,
      origin: g.origin,
      name: g.label,
    }));
    const { ok, data } = await call<SpecDraft>("v2", {
      objective,
      type,
      name: name.trim(),
      goals: { ...goals, available },
      ways,
    });
    if (!ok) {
      setBusy(false);
      setTrouble(said(data, "The draft could not be made."));
      return;
    }
    router.push(`/campaigns/new/${data.id}?step=${data.steps[1]?.id ?? "bidding"}`);
  }

  return (
    <div className="flex flex-col gap-5">
      <Card
        title="Choose your objective"
        help="Select an objective to tailor your experience to the goals and settings that will work best for your campaign."
      >
        <div className="p-6">
          <ObjectiveTiles
            setup={setup}
            value={objective}
            onChange={(next) => {
              setObjective(next);
              if (type && !setup.objectives[next].types.includes(type)) setType(null);
            }}
          />
        </div>
      </Card>

      {o && o.goals ? (
        <Card title={`Use these conversion goals to improve ${o.label}`}>
          <div className="p-6">
            <GoalsTable setup={setup} goals={goals} onChange={setGoals} />
          </div>
        </Card>
      ) : null}

      {objective ? (
        <Card title="Select a campaign type">
          <div className="p-6">
            <TypeTiles setup={setup} objective={objective} value={type} onChange={setType} />
          </div>
        </Card>
      ) : null}

      {type ? (
        <Card
          title="Select the ways you'd like to reach your goal"
          help="You can enter additional information about your business."
        >
          <div className="p-6">
            <WaysToReach ways={ways} onChange={setWays} type={type} />
          </div>
        </Card>
      ) : null}

      {type ? (
        <Card title="Campaign name" help="Customers never see it.">
          <div className="p-6">
            <Input
              value={name}
              maxLength={255}
              aria-label="Campaign name"
              placeholder={`${typeLabel}-${o?.label ?? "Campaign"}-1`}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
        </Card>
      ) : null}

      {trouble ? <Note tone="bad">{trouble}</Note> : null}

      <div className="flex items-center justify-end gap-3">
        <Link href="/campaigns" className="text-pw-ink-600 text-[14px] font-semibold">
          Cancel
        </Link>
        <Button onClick={start} disabled={!ready} working={busy ? "Making the draft…" : false}>
          Continue <ArrowRightIcon className="size-4" />
        </Button>
      </div>
      {!ready && type ? (
        <p className="text-pw-ink-500 -mt-3 text-right text-[13px]">
          {!ways.website_url.trim() ? "Add your website. " : ""}
          {!name.trim() ? "Name the campaign." : ""}
        </p>
      ) : null}
    </div>
  );
}
