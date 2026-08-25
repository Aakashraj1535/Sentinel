import { createFileRoute } from "@tanstack/react-router";
import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2, Clock, DollarSign, Gauge, ShieldAlert } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { ExceptionTable } from "@/components/ExceptionTable";
import { SummaryStat } from "@/components/SummaryStat";
import { TriggerPipelineButton } from "@/components/TriggerPipelineButton";
import { SendReportButton } from "@/components/SendReportButton";
import { AnalyticsCharts } from "@/components/analytics/AnalyticsCharts";
import { SystemHealthStrip } from "@/components/SystemHealthStrip";
import { SystemicPatternsPanel } from "@/components/SystemicPatternsPanel";
import { RootCauseAnalysisPanel } from "@/components/RootCauseAnalysisPanel";
import { FinancialImpactPanel } from "@/components/FinancialImpactPanel";
import { CalibrationCard } from "@/components/CalibrationCard";
import {
  getDashboardSummary,
  getExceptions,
  type ExceptionRecord,
} from "@/lib/mock-api";

export const Route = createFileRoute("/")({
  component: DashboardPage,
});

type Summary = Awaited<ReturnType<typeof getDashboardSummary>>;

function DashboardPage() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [exceptions, setExceptions] = useState<ExceptionRecord[]>([]);
  const [reloadKey, setReloadKey] = useState(0);

  const refresh = useCallback(() => setReloadKey((k) => k + 1), []);

  useEffect(() => {
    getDashboardSummary().then(setSummary);
    getExceptions().then(setExceptions);
  }, [reloadKey]);

  return (
    <AppShell>
      <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">
            Operations Dashboard
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Live view of detected supply chain exceptions and AI-recommended
            resolutions.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="hidden sm:flex items-center gap-2 rounded-md border border-border bg-surface px-3 py-1.5 text-xs text-muted-foreground">
            <span className="h-2 w-2 rounded-full bg-success animate-pulse" />
            Monitoring live
          </div>
          <TriggerPipelineButton onComplete={refresh} />
          <SendReportButton />
        </div>
      </div>

      <div className="mb-6">
        <SystemHealthStrip />
      </div>



      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-7 mb-8">
        <SummaryStat
          label="Active exceptions"
          value={summary?.activeCount ?? "—"}
          hint="Awaiting resolution"
          tone="info"
          icon={<AlertTriangle className="h-4 w-4" />}
        />
        <SummaryStat
          label="Resolved today"
          value={summary?.resolvedToday ?? "—"}
          hint="Auto & manual"
          tone="success"
          icon={<CheckCircle2 className="h-4 w-4" />}
        />
        <SummaryStat
          label="SLA breached"
          value={summary?.slaBreachedCount ?? "—"}
          hint="Past response deadline"
          tone="danger"
          icon={<AlertTriangle className="h-4 w-4" />}
        />
        <SummaryStat
          label="SLA at risk"
          value={summary?.slaAtRiskCount ?? "—"}
          hint="Approaching deadline"
          tone="warning"
          icon={<Clock className="h-4 w-4" />}
        />
        <SummaryStat
          label="Avg. confidence"
          value={summary ? `${summary.avgConfidence}%` : "—"}
          hint="Across all recommendations"
          icon={<Gauge className="h-4 w-4" />}
        />
        <SummaryStat
          label="Escalations pending"
          value={summary?.escalationsPending ?? "—"}
          hint="Human review required"
          tone="danger"
          icon={<ShieldAlert className="h-4 w-4" />}
        />
        <SummaryStat
          label="Financial impact at risk"
          value={
            summary
              ? summary.totalFinancialImpactAtRisk.toLocaleString(undefined, {
                  style: "currency",
                  currency: "USD",
                  maximumFractionDigits: 0,
                })
              : "—"
          }
          hint="Open exceptions, estimated"
          tone="warning"
          icon={<DollarSign className="h-4 w-4" />}
        />
      </div>

      <div className="mb-8">
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-muted-foreground">
          Analytics
        </h2>
        <AnalyticsCharts key={reloadKey} />
      </div>

      <div className="mb-8 grid grid-cols-1 gap-6 xl:grid-cols-2">
        <RootCauseAnalysisPanel />
        <FinancialImpactPanel />
      </div>

      <div className="mb-8 grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <SystemicPatternsPanel />
        </div>
        <CalibrationCard />
      </div>


      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
          Detected exceptions
        </h2>
        <span className="text-xs text-muted-foreground">
          {exceptions.length} total
        </span>
      </div>
      <ExceptionTable rows={exceptions} />
    </AppShell>
  );
}
