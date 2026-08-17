import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { PieChart as PieChartIcon } from "lucide-react";
import { toast } from "sonner";
import {
  fetchRootCauseBreakdown,
  type RootCauseBreakdown,
} from "@/lib/insights-api";
import { Skeleton } from "@/components/ui/skeleton";

// One consistent color per category across both the breakdown and the
// trend chart, so the two views read as the same data, not two
// unrelated charts that happen to sit next to each other.
const CATEGORY_COLORS: Record<string, string> = {
  "Port / logistics congestion": "var(--chart-1, #6366f1)",
  "Customs / documentation": "var(--chart-2, #f59e0b)",
  "Supplier capacity issues": "var(--chart-3, #ef4444)",
  "Quality control": "var(--chart-4, #10b981)",
  Other: "var(--muted-foreground)",
  Uncategorized: "var(--border)",
};

function colorFor(category: string): string {
  return CATEGORY_COLORS[category] ?? "var(--muted-foreground)";
}

export function RootCauseAnalysisPanel() {
  const [data, setData] = useState<RootCauseBreakdown | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetchRootCauseBreakdown()
      .then((d) => {
        if (!cancelled) setData(d);
      })
      .catch((e) => {
        if (!cancelled) {
          toast.error(e instanceof Error ? e.message : "Failed to load root cause data");
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

  const overallEntries = Object.entries(data.overall)
    .filter(([, count]) => count > 0)
    .sort((a, b) => b[1] - a[1]);
  const totalTagged = overallEntries.reduce((sum, [, c]) => sum + c, 0);

  return (
    <section className="rounded-lg border border-border bg-surface p-5">
      <div className="mb-1 flex items-center gap-2">
        <PieChartIcon className="h-4 w-4 text-muted-foreground" />
        <h2 className="text-sm font-semibold text-foreground">Root Cause Analysis</h2>
      </div>
      <p className="mb-4 text-xs text-muted-foreground">
        What's actually driving exceptions, and whether it's trending up or down.
      </p>

      {totalTagged === 0 ? (
        <div className="rounded-md border border-dashed border-border bg-background/40 p-6 text-center">
          <p className="text-sm text-muted-foreground">
            No categorized root causes yet — this fills in automatically as
            exceptions are resolved.
          </p>
        </div>
      ) : (
        <>
          <div className="mb-5 space-y-2">
            {overallEntries.map(([category, count]) => {
              const pct = Math.round((count / totalTagged) * 100);
              return (
                <div key={category} className="flex items-center gap-3">
                  <span
                    className="h-2.5 w-2.5 shrink-0 rounded-full"
                    style={{ backgroundColor: colorFor(category) }}
                  />
                  <span className="w-48 shrink-0 truncate text-xs text-foreground">
                    {category}
                  </span>
                  <div className="h-2 flex-1 overflow-hidden rounded-full bg-muted">
                    <div
                      className="h-full rounded-full"
                      style={{ width: `${pct}%`, backgroundColor: colorFor(category) }}
                    />
                  </div>
                  <span className="w-16 shrink-0 text-right text-xs tabular-nums text-muted-foreground">
                    {count} ({pct}%)
                  </span>
                </div>
              );
            })}
          </div>

          {data.trend.length > 1 && (
            <div className="h-56">
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
                  <YAxis tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{
                      background: "var(--surface)",
                      border: "1px solid var(--border)",
                      borderRadius: 8,
                      fontSize: 12,
                    }}
                  />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  {data.categories.map((cat) => (
                    <Bar key={cat} dataKey={cat} stackId="a" fill={colorFor(cat)} />
                  ))}
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </>
      )}
    </section>
  );
}
