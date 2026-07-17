import { useEffect, useState } from "react";
import {
  ArrowDownRight,
  ArrowUpRight,
  Loader2,
  Minus,
  RefreshCw,
  Sparkles,
} from "lucide-react";
import { toast } from "sonner";
import {
  fetchPredictiveRisk,
  refreshPredictiveRisk,
  type PredictedRiskLevel,
  type PredictiveRiskForecast,
  type RiskTrend,
} from "@/lib/predictive-risk-api";
import { cn } from "@/lib/utils";

function RiskLevelBadge({ level }: { level: PredictedRiskLevel }) {
  const map: Record<PredictedRiskLevel, string> = {
    Low: "bg-[color-mix(in_oklab,var(--success)_15%,transparent)] text-[color-mix(in_oklab,var(--success)_50%,black)] border-[color-mix(in_oklab,var(--success)_30%,transparent)]",
    Medium:
      "bg-[color-mix(in_oklab,var(--warning)_18%,transparent)] text-[color-mix(in_oklab,var(--warning)_55%,black)] border-[color-mix(in_oklab,var(--warning)_35%,transparent)]",
    High: "bg-[color-mix(in_oklab,var(--danger)_15%,transparent)] text-[color-mix(in_oklab,var(--danger)_60%,black)] border-[color-mix(in_oklab,var(--danger)_35%,transparent)]",
  };
  const dot: Record<PredictedRiskLevel, string> = {
    Low: "bg-success",
    Medium: "bg-warning",
    High: "bg-danger",
  };
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium border",
        map[level],
      )}
    >
      <span className={cn("h-1.5 w-1.5 rounded-full", dot[level])} />
      {level} predicted
    </span>
  );
}

function TrendIndicator({ trend }: { trend: RiskTrend }) {
  if (trend === "Rising") {
    return (
      <span className="inline-flex items-center gap-1 text-xs font-medium text-danger">
        <ArrowUpRight className="h-3.5 w-3.5" />
        Rising
      </span>
    );
  }
  if (trend === "Improving") {
    return (
      <span className="inline-flex items-center gap-1 text-xs font-medium text-success">
        <ArrowDownRight className="h-3.5 w-3.5" />
        Improving
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 text-xs font-medium text-muted-foreground">
      <Minus className="h-3.5 w-3.5" />
      Stable
    </span>
  );
}

export function PredictiveRiskPanel() {
  const [forecasts, setForecasts] = useState<PredictiveRiskForecast[] | null>(
    null,
  );
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    fetchPredictiveRisk()
      .then(setForecasts)
      .catch(() => setForecasts([]))
      .finally(() => setLoading(false));
  }, []);

  async function handleRefresh() {
    setRefreshing(true);
    try {
      const result = await refreshPredictiveRisk();
      setForecasts(result.results);
      toast.success(
        `Analyzed ${result.suppliers_analyzed} supplier${result.suppliers_analyzed === 1 ? "" : "s"}`,
      );
    } catch {
      toast.error("Failed to refresh predictive risk forecast.");
    } finally {
      setRefreshing(false);
    }
  }

  return (
    <section className="rounded-lg border border-border bg-surface p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="flex items-center gap-2 text-lg font-semibold tracking-tight">
            <Sparkles className="h-4 w-4 text-muted-foreground" />
            Predictive Risk Forecast
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Proactive risk detection — flags suppliers trending toward problems
            before a new exception occurs.
          </p>
        </div>
        <div className="flex items-center gap-3">
          {refreshing && (
            <span className="hidden sm:inline text-xs text-muted-foreground">
              Analyzing supplier trends...
            </span>
          )}
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className={cn(
              "inline-flex items-center gap-2 rounded-md bg-primary px-3.5 py-2 text-sm font-medium text-primary-foreground shadow-sm transition-colors",
              "hover:opacity-90 disabled:opacity-70 disabled:cursor-not-allowed",
            )}
          >
            {refreshing ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4" />
            )}
            {refreshing ? "Analyzing..." : "Refresh Forecast"}
          </button>
        </div>
      </div>

      <div className="mt-5">
        {loading || refreshing ? (
          <div className="space-y-2">
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                className="h-16 animate-pulse rounded-md border border-border bg-muted/40"
              />
            ))}
          </div>
        ) : !forecasts || forecasts.length === 0 ? (
          <div className="rounded-md border border-dashed border-border bg-background/60 p-8 text-center">
            <p className="text-sm text-muted-foreground">
              No forecast yet — click Refresh Forecast to run the first
              analysis.
            </p>
          </div>
        ) : (
          <ul className="divide-y divide-border overflow-hidden rounded-md border border-border">
            {forecasts.map((f) => (
              <li
                key={f.supplierId}
                className="bg-background/40 px-4 py-3.5 hover:bg-accent/30 transition-colors"
              >
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{f.supplierName}</span>
                      <span className="font-mono text-xs text-muted-foreground">
                        {f.supplierId}
                      </span>
                    </div>
                    <div className="mt-1 flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
                      <TrendIndicator trend={f.trend} />
                      <span className="tabular-nums">
                        <span className="font-medium text-foreground">
                          {f.recentIncidentCount}
                        </span>{" "}
                        recent vs{" "}
                        <span className="font-medium text-foreground">
                          {f.priorIncidentCount}
                        </span>{" "}
                        prior
                      </span>
                    </div>
                  </div>
                  <RiskLevelBadge level={f.predictedRiskLevel} />
                </div>
                <p className="mt-2 text-sm leading-relaxed text-foreground">
                  {f.explanation}
                </p>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
