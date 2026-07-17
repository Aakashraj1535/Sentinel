import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { BarChart3, TrendingUp } from "lucide-react";
import {
  fetchAnalyticsSummary,
  type AnalyticsSummary,
} from "@/lib/backend-api";

const SEVERITY_COLORS: Record<string, string> = {
  Low: "var(--muted-foreground)",
  Medium: "var(--warning)",
  High: "var(--danger)",
};

export function AnalyticsCharts() {
  const [data, setData] = useState<AnalyticsSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetchAnalyticsSummary()
      .then((d) => {
        if (!cancelled) setData(d);
      })
      .catch(() => {
        if (!cancelled) setError("Unable to load analytics.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return (
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            className="h-64 rounded-lg border border-border bg-surface animate-pulse"
          />
        ))}
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="rounded-lg border border-border bg-surface p-8 text-center text-sm text-muted-foreground">
        {error ?? "No analytics data available."}
      </div>
    );
  }

  const severityData = (["Low", "Medium", "High"] as const).map((k) => ({
    name: k,
    value: data.severityDistribution[k] ?? 0,
  }));
  const hasAny =
    severityData.some((d) => d.value > 0) ||
    data.typeDistribution.length > 0 ||
    data.resolutionTrend.length > 0;

  if (!hasAny) {
    return (
      <div className="rounded-lg border border-border bg-surface p-10 text-center">
        <BarChart3 className="h-6 w-6 mx-auto text-muted-foreground mb-2" />
        <p className="text-sm text-muted-foreground">
          No analytics data yet — run the pipeline to generate exceptions.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <AutoResolvedCard
          rate={data.autoResolvedRate}
          total={data.totalProcessed}
        />
        <ChartPanel title="Severity distribution">
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie
                data={severityData}
                dataKey="value"
                nameKey="name"
                innerRadius={45}
                outerRadius={75}
                paddingAngle={2}
              >
                {severityData.map((entry) => (
                  <Cell
                    key={entry.name}
                    fill={SEVERITY_COLORS[entry.name]}
                  />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  background: "var(--surface)",
                  border: "1px solid var(--border)",
                  borderRadius: 6,
                  fontSize: 12,
                }}
              />
              <Legend
                wrapperStyle={{ fontSize: 12 }}
                iconType="circle"
              />
            </PieChart>
          </ResponsiveContainer>
        </ChartPanel>

        <ChartPanel title="Exception types">
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={data.typeDistribution}>
              <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" vertical={false} />
              <XAxis
                dataKey="type"
                tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
                interval={0}
                angle={-15}
                textAnchor="end"
                height={50}
              />
              <YAxis
                tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
                allowDecimals={false}
              />
              <Tooltip
                contentStyle={{
                  background: "var(--surface)",
                  border: "1px solid var(--border)",
                  borderRadius: 6,
                  fontSize: 12,
                }}
              />
              <Bar dataKey="count" fill="var(--primary)" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartPanel>
      </div>

      <ChartPanel title="Resolution trend" icon={<TrendingUp className="h-4 w-4" />}>
        <ResponsiveContainer width="100%" height={260}>
          <LineChart data={data.resolutionTrend}>
            <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" vertical={false} />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
            />
            <YAxis
              tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
              allowDecimals={false}
            />
            <Tooltip
              contentStyle={{
                background: "var(--surface)",
                border: "1px solid var(--border)",
                borderRadius: 6,
                fontSize: 12,
              }}
            />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            <Line
              type="monotone"
              dataKey="resolved"
              stroke="var(--success)"
              strokeWidth={2}
              dot={false}
            />
            <Line
              type="monotone"
              dataKey="escalated"
              stroke="var(--danger)"
              strokeWidth={2}
              dot={false}
            />
            <Line
              type="monotone"
              dataKey="active"
              stroke="var(--info)"
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </ChartPanel>
    </div>
  );
}

function ChartPanel({
  title,
  icon,
  children,
}: {
  title: string;
  icon?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-lg border border-border bg-surface p-5">
      <h3 className="flex items-center gap-2 text-xs uppercase tracking-wider font-medium text-muted-foreground mb-4">
        {icon}
        {title}
      </h3>
      {children}
    </section>
  );
}

function AutoResolvedCard({ rate, total }: { rate: number; total: number }) {
  return (
    <div className="rounded-lg border border-border bg-surface p-5 flex flex-col justify-between">
      <div className="text-xs uppercase tracking-wider font-medium text-muted-foreground">
        Auto-Resolved Without Escalation
      </div>
      <div className="mt-4">
        <div className="text-5xl font-semibold tabular-nums text-success">
          {rate.toFixed(1)}%
        </div>
        <div className="mt-2 text-xs text-muted-foreground">
          out of {total} total exception{total === 1 ? "" : "s"}
        </div>
      </div>
    </div>
  );
}
