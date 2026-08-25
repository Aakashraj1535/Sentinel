import { useState } from "react";
import { useRouter } from "@tanstack/react-router";
import { DollarSign, Loader2, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { recomputeFinancialImpact } from "@/lib/human-review-api";
import { useHasRole } from "@/hooks/use-role";
import type { ExceptionRecord } from "@/lib/mock-api";

function formatUsd(value: number): string {
  return value.toLocaleString(undefined, {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  });
}

/**
 * Shows the estimated dollar exposure for one exception -- the
 * deterministic figure computed by app/financial_impact.py (order value
 * x severity% + SLA breach add-on), plus the LLM-generated one-sentence
 * explanation from agents/financial_impact_agent.py. The number itself
 * never comes from the LLM, only the explanation text does -- see the
 * breakdown row for exactly how the figure was derived.
 */
export function FinancialImpactCard({ ex }: { ex: ExceptionRecord }) {
  const router = useRouter();
  const [recomputing, setRecomputing] = useState(false);
  const canRecompute = useHasRole("Procurement Manager");

  async function handleRecompute() {
    setRecomputing(true);
    try {
      await recomputeFinancialImpact(ex.id);
      toast.success("Financial impact recomputed");
      await router.invalidate();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to recompute financial impact");
    } finally {
      setRecomputing(false);
    }
  }

  const breakdown = ex.financialImpactBreakdown;
  const hasEstimate = ex.estimatedFinancialImpact != null && breakdown != null;

  return (
    <section className="rounded-lg border border-border bg-surface p-5">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="flex items-center gap-2 text-sm font-semibold text-foreground">
          <DollarSign className="h-4 w-4 text-muted-foreground" />
          Financial impact
        </h2>
        {canRecompute && (
          <button
            onClick={handleRecompute}
            disabled={recomputing}
            className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground disabled:opacity-60"
            title="Recompute using current order value and SLA status"
          >
            {recomputing ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <RefreshCw className="h-3.5 w-3.5" />
            )}
            Recompute
          </button>
        )}
      </div>

      {!hasEstimate ? (
        <p className="text-sm text-muted-foreground">
          {ex.financialImpactExplanation ??
            "Not yet estimated — this fills in automatically once the exception is processed."}
        </p>
      ) : (
        <>
          <div className="mb-3 text-2xl font-semibold tabular-nums text-foreground">
            {formatUsd(ex.estimatedFinancialImpact as number)}
          </div>

          {ex.financialImpactExplanation && (
            <p className="mb-4 text-sm leading-relaxed text-foreground">
              {ex.financialImpactExplanation}
            </p>
          )}

          <div className="space-y-1.5 rounded-md border border-border bg-background/40 p-3 text-xs">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Order value</span>
              <span className="tabular-nums text-foreground">{formatUsd(breakdown.orderValue)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Severity exposure ({breakdown.severity})</span>
              <span className="tabular-nums text-foreground">
                {(breakdown.severityPct * 100).toFixed(0)}%
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">
                SLA breach add-on {breakdown.slaBreached ? "" : "(not breached)"}
              </span>
              <span className="tabular-nums text-foreground">
                {breakdown.slaBreached ? `+${(breakdown.slaBreachAddOnPct * 100).toFixed(0)}%` : "—"}
              </span>
            </div>
            <div className="mt-1 flex justify-between border-t border-border pt-1.5 font-medium">
              <span className="text-foreground">Total exposure</span>
              <span className="tabular-nums text-foreground">
                {(breakdown.totalPct * 100).toFixed(0)}%
              </span>
            </div>
          </div>
        </>
      )}
    </section>
  );
}
