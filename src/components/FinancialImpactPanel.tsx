import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { DollarSign } from "lucide-react";
import { toast } from "sonner";
import {
  fetchFinancialImpactSummary,
  type FinancialImpactSummary,
} from "@/lib/insights-api";
import { Skeleton } from "@/components/ui/skeleton";

const SEVERITY_COLORS: Record<string, string> = {
  Low: "var(--chart-4, #10b981)",
  Medium: "var(--chart-2, #f59e0b)",
  High: "var(--chart-3, #ef4444)",
};

function formatInr(value: number): string {
  return value.toLocaleString("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  });
}

export function FinancialImpactPanel() {
  const [data, setData] = useState<FinancialImpactSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetchFinancialImpactSummary()
      .then((d) => {
        if (!cancelled) setData(d);
      })
      .catch((e) => {
        if (!cancelled) {
          toast.error(e instanceof Error ? e.message : "Failed to load financial impact data");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return <Skeleton className="h-72 w-full rounded-lg" />;
  }

  if (!data) return null;

  const severityEntries = Object.entries(data.bySeverity).filter(([, b]) => b.count > 0);
  const hasAnyData = data.pricedExceptionCount > 0 || data.trend.length > 0;

  return (
    <section className="rounded-lg border border-border bg-surface p-5">
      <div className="mb-1 flex items-center gap-2">
        <DollarSign className="h-4 w-4 text-muted-foreground" />
        <h2 className="text-sm font-semibold text-foreground">Financial Impact</h2>
      </div>
      <p className="mb-4 text-xs text-muted-foreground">
        Estimated dollars at risk across open exceptions, based on order value,
        severity, and SLA status.
      </p>

      {!hasAnyData ? (
        <div className="rounded-md border border-dashed border-border bg-background/40 p-6 text-center">
          <p className="text-sm text-muted-foreground">
            No priced exceptions yet — run{" "}
            <code className="rounded bg-muted px-1 py-0.5 text-xs">
              db/backfill_unit_cost.py
            </code>{" "}
            to set a cost basis on existing orders, then re-run the pipeline.
          </p>
        </div>
      ) : (
        <>
          <div className="mb-5 flex flex-wrap items-end gap-6">
            <div>
              <div className="text-2xl font-semibold tabular-nums text-foreground">
                {formatInr(data.totalAtRisk)}
              </div>
              <div className="text-xs text-muted-foreground">
                Currently at risk ({data.pricedExceptionCount} priced exception
                {data.pricedExceptionCount === 1 ? "" : "s"})
              </div>
            </div>
            {data.unpricedExceptionCount > 0 && (
              <div className="text-xs text-muted-foreground">
                {data.unpricedExceptionCount} open exception
                {data.unpricedExceptionCount === 1 ? "" : "s"} still unpriced
                (no order/unit cost linked)
              </div>
            )}
          </div>

          {severityEntries.length > 0 && (
            <div className="mb-5 space-y-2">
              {severityEntries.map(([severity, bucket]) => {
                const pct = data.totalAtRisk > 0 ? Math.round((bucket.total / data.totalAtRisk) * 100) : 0;
                return (
                  <div key={severity} className="flex items-center gap-3">
                    <span
                      className="h-2.5 w-2.5 shrink-0 rounded-full"
                      style={{ backgroundColor: SEVERITY_COLORS[severity] ?? "var(--muted-foreground)" }}
                    />
                    <span className="w-20 shrink-0 text-xs text-foreground">{severity}</span>
                    <div className="h-2 flex-1 overflow-hidden rounded-full bg-muted">
                      <div
                        className="h-full rounded-full"
                        style={{
                          width: `${pct}%`,
                          backgroundColor: SEVERITY_COLORS[severity] ?? "var(--muted-foreground)",
                        }}
                      />
                    </div>
                    <span className="w-28 shrink-0 text-right text-xs tabular-nums text-muted-foreground">
                      {formatInr(bucket.total)} ({bucket.count})
                    </span>
                  </div>
                );
              })}
            </div>
          )}

          {data.topSuppliers.length > 0 && (
            <div className="mb-5">
              <h3 className="mb-2 text-xs font-medium text-muted-foreground">
                Top suppliers by exposure
              </h3>
              <div className="space-y-1.5">
                {data.topSuppliers.map((s) => (
                  <div key={s.supplier} className="flex items-center justify-between text-xs">
                    <span className="text-foreground">{s.supplier}</span>
                    <span className="tabular-nums text-muted-foreground">
                      {formatInr(s.total)} ({s.count})
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {data.trend.length > 1 && (
            <div className="h-48">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data.trend}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis
                    dataKey="week"
                    tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
                    tickFormatter={(v: string) =>
                      new Date(v).toLocaleDateString(undefined, { month: "short", day: "numeric" })
                    }
                  />
                  <YAxis
                    tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
                    tickFormatter={(v: number) => formatInr(v)}
                  />
                  <Tooltip
                    formatter={(v: number) => formatInr(v)}
                    contentStyle={{
                      background: "var(--surface)",
                      border: "1px solid var(--border)",
                      borderRadius: 8,
                      fontSize: 12,
                    }}
                  />
                  <Bar dataKey="total" fill="var(--chart-1, #6366f1)" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </>
      )}
    </section>
  );
}
