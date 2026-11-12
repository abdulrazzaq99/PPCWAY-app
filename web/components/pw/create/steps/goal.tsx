"use client";

import { Input } from "@/components/ui/field";
import type { StepProps } from "../editor";
import { GoalsTable, OBJECTIVE_ICON, TYPE_ICON, WaysToReach } from "../goal-parts";
import { Card, Note, Problems } from "../kit";

/*
  Step 1 again, after the draft exists: the goals, the ways to reach them and
  the name can change; the objective and campaign type cannot, as in Google,
  where a different type is a different campaign.
*/
export function StepGoal({ spec, setup, change, problems }: StepProps) {
  const o = setup.objectives[spec.objective];
  const t = setup.types[spec.type];
  const ObjectiveIcon = OBJECTIVE_ICON[spec.objective];
  const TypeIcon = TYPE_ICON[spec.type];
  return (
    <div className="flex flex-col gap-5">
      <Problems items={problems} />
      <Card title="Objective and campaign type">
        <div className="flex flex-wrap gap-6 p-6">
          <div className="flex items-center gap-3">
            <ObjectiveIcon className="text-pw-blue size-7" />
            <div>
              <p className="text-pw-ink-500 text-[12px]">Objective</p>
              <p className="text-pw-ink text-[15px] font-semibold">{o?.label}</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {TypeIcon ? <TypeIcon className="text-pw-blue size-7" /> : null}
            <div>
              <p className="text-pw-ink-500 text-[12px]">Campaign type</p>
              <p className="text-pw-ink text-[15px] font-semibold">{t?.label}</p>
            </div>
          </div>
        </div>
        <div className="px-6 pb-6">
          <Note>
            To use a different objective or type, start a new campaign. Google does not change them
            on a campaign in progress.
          </Note>
        </div>
      </Card>
      {o?.goals ? (
        <Card title={`Use these conversion goals to improve ${o.label}`}>
          <div className="p-6">
            <GoalsTable setup={setup} goals={spec.goals} onChange={(g) => change("goals", g)} />
          </div>
        </Card>
      ) : null}
      <Card title="Select the ways you'd like to reach your goal">
        <div className="p-6">
          <WaysToReach ways={spec.ways} onChange={(w) => change("ways", w)} type={spec.type} />
        </div>
      </Card>
      <Card title="Campaign name" help="Customers never see it.">
        <div className="p-6">
          <Input
            value={spec.name}
            maxLength={255}
            aria-label="Campaign name"
            onChange={(e) => change("name", e.target.value)}
          />
        </div>
      </Card>
    </div>
  );
}
