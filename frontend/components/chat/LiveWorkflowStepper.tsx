import { Check, Loader2 } from "lucide-react";
import type { RouteDecision } from "@/lib/types";
import { cn } from "@/lib/utils";

const REACT_STEPS = ["triage", "retrieve", "diagnose", "resolve", "memwrite"];
const DAG_STEPS_BY_INTENT: Record<string, string[]> = {
  password_reset: ["validate", "policy", "reset_password", "memwrite"],
  account_unlock: ["validate", "policy", "unlock_account", "memwrite"],
  mfa_reset: ["validate", "policy", "reset_mfa", "memwrite"],
  request_software: ["validate", "policy", "file_ticket", "memwrite"],
  distribution_list_access: ["validate", "policy", "file_ticket", "memwrite"],
};

export function LiveWorkflowStepper({
  route,
  phase,
  phaseHistory,
}: {
  route?: RouteDecision;
  phase?: string;
  phaseHistory?: string[];
}) {
  if (!route) return null;
  const isDag = route.route === "dag";
  const steps = isDag
    ? DAG_STEPS_BY_INTENT[route.intent ?? ""] ?? ["validate", "policy", "execute", "memwrite"]
    : REACT_STEPS;
  const seen = new Set(phaseHistory ?? []);
  const current = phase ?? null;

  return (
    <div className="flex items-center flex-wrap gap-1 mb-2">
      <span className="text-[10px] uppercase tracking-wider text-muted mr-1">
        {isDag ? "DAG flow" : "ReAct loop"}
      </span>
      {steps.map((s, i) => {
        const done = seen.has(s) && s !== current;
        const live = s === current || (isDag && i === Math.min(steps.length - 1, seen.size));
        return (
          <span
            key={s}
            className={cn(
              "inline-flex items-center gap-1 px-1.5 py-0.5 rounded border text-[10px]",
              done
                ? "border-ok/40 text-ok bg-ok/10"
                : live
                  ? "border-accent/60 text-accent bg-accent/10 animate-pulse"
                  : "border-zinc-700 text-zinc-500 bg-zinc-800/30",
            )}
          >
            {done ? (
              <Check className="w-2.5 h-2.5" />
            ) : live ? (
              <Loader2 className="w-2.5 h-2.5 animate-spin" />
            ) : (
              <span className="w-2.5 h-2.5" />
            )}
            <span>{s}</span>
          </span>
        );
      })}
    </div>
  );
}
