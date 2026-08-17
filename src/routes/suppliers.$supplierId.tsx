import { createFileRoute, Link, notFound } from "@tanstack/react-router";
import {
  Line,
  LineChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  ReferenceLine,
} from "recharts";
import { ArrowLeft, Package } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { RiskBadge } from "@/components/RiskBadge";
import { SeverityBadge } from "@/components/StatusBadges";
import { TrendBadge } from "@/components/TrendBadge";
import { getSuppliers, type Supplier } from "@/lib/mock-api";
import { fetchSupplierTrend, type SupplierTrend } from "@/lib/insights-api";

export const Route = createFileRoute("/suppliers/$supplierId")({
  loader: async ({ params }) => {
    // No single-supplier GET endpoint exists yet — the supplier list is
    // small enough that fetching it and finding by id client-side is
    // simpler than adding a new backend endpoint just for this.
    const suppliers = await getSuppliers();
    const supplier = suppliers.find((s) => s.id === params.supplierId);
    if (!supplier) throw notFound();
    const trend = await fetchSupplierTrend(params.supplierId);
    return { supplier, trend };
  },
  component: SupplierDetailPage,
  notFoundComponent: () => (
    <AppShell>
      <div className="rounded-lg border border-border bg-surface p-10 text-center">
        <h2 className="text-lg font-semibold">Supplier not found</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          The requested supplier ID doesn't exist.
        </p>
        <Link
          to="/suppliers"
          className="mt-4 inline-flex items-center gap-1.5 text-sm text-primary hover:underline"
        >
          <ArrowLeft className="h-4 w-4" /> Back to suppliers
        </Link>
      </div>
    </AppShell>
  ),
  // Without this, a failed loader (e.g. the backend not having been
  // restarted after this endpoint was added, or any other fetch error)
  // has nothing to render and can silently fail the navigation instead
  // of showing anything -- this makes failures visible and actionable.
  errorComponent: ({ error }) => (
    <AppShell>
      <div className="rounded-lg border border-border bg-surface p-10 text-center">
        <h2 className="text-lg font-semibold">Couldn't load this supplier</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          {error instanceof Error ? error.message : "Something went wrong loading this page."}
        </p>
        <p className="mt-1 text-xs text-muted-foreground">
          If this just started happening, make sure your backend has been
          restarted after the latest update.
        </p>
        <Link
          to="/suppliers"
          className="mt-4 inline-flex items-center gap-1.5 text-sm text-primary hover:underline"
        >
          <ArrowLeft className="h-4 w-4" /> Back to suppliers
        </Link>
      </div>
    </AppShell>
  ),
});

function SupplierDetailPage() {
  const { supplier, trend } = Route.useLoaderData() as {
    supplier: Supplier;
    trend: SupplierTrend;
  };

  const hasTrendData = trend.weeklySeries.length > 0;

  return (
    <AppShell>
      <Link
        to="/suppliers"
        className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground mb-4"
      >
        <ArrowLeft className="h-4 w-4" /> Back to suppliers
      </Link>

      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{supplier.name}</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {supplier.region} · <span className="font-mono">{supplier.id}</span>
          </p>
        </div>
        <div className="flex items-center gap-2">
          <RiskBadge level={supplier.riskLevel} />
          <TrendBadge direction={trend.trendDirection} />
        </div>
      </div>

      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-lg border border-border bg-surface p-4">
          <div className="text-xs text-muted-foreground">Current on-time rate</div>
          <div className="mt-1 text-2xl font-semibold tabular-nums">
            {supplier.onTimeRate.toFixed(1)}%
          </div>
        </div>
        <div className="rounded-lg border border-border bg-surface p-4">
          <div className="text-xs text-muted-foreground">Total incidents</div>
          <div className="mt-1 text-2xl font-semibold tabular-nums">
            {supplier.totalIncidents}
          </div>
        </div>
        <div className="rounded-lg border border-border bg-surface p-4">
          <div className="text-xs text-muted-foreground">
            Recent vs. prior period
          </div>
          <div className="mt-1 text-2xl font-semibold tabular-nums">
            {trend.recentOnTimeRate}%
            <span className="ml-2 text-sm font-normal text-muted-foreground">
              (was {trend.priorOnTimeRate}%)
            </span>
          </div>
        </div>
      </div>

      <section className="mb-6 rounded-lg border border-border bg-surface p-5">
        <div className="mb-1 flex items-center gap-2">
          <Package className="h-4 w-4 text-muted-foreground" />
          <h2 className="text-sm font-semibold text-foreground">
            On-Time Delivery Rate Over Time
          </h2>
        </div>
        <p className="mb-4 text-xs text-muted-foreground">
          Computed from actual delivered orders, not a static snapshot —
          this is what changed week over week, not just where things stand today.
        </p>

        {!hasTrendData ? (
          <div className="rounded-md border border-dashed border-border bg-background/40 p-8 text-center">
            <p className="text-sm text-muted-foreground">
              No delivered orders on record for this supplier yet — the trend
              fills in as orders complete.
            </p>
          </div>
        ) : (
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trend.weeklySeries}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis
                  dataKey="week"
                  tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
                  tickFormatter={(v: string) =>
                    new Date(v).toLocaleDateString(undefined, { month: "short", day: "numeric" })
                  }
                />
                <YAxis
                  domain={[0, 100]}
                  tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
                  tickFormatter={(v) => `${v}%`}
                />
                <ReferenceLine y={90} stroke="var(--border)" strokeDasharray="4 4" />
                <Tooltip
                  contentStyle={{
                    background: "var(--surface)",
                    border: "1px solid var(--border)",
                    borderRadius: 8,
                    fontSize: 12,
                  }}
                  formatter={(value: number, name: string, props) => [
                    `${value}% (${props.payload.orderCount} order${props.payload.orderCount === 1 ? "" : "s"})`,
                    "On-time rate",
                  ]}
                />
                <Line
                  type="monotone"
                  dataKey="onTimeRate"
                  stroke="var(--primary)"
                  strokeWidth={2}
                  dot={{ r: 3 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </section>

      <section className="rounded-lg border border-border bg-surface p-5">
        <h2 className="mb-4 text-sm font-semibold text-foreground">Recent Incidents</h2>
        {supplier.recentIncidents.length === 0 ? (
          <p className="text-sm text-muted-foreground">No incidents recorded.</p>
        ) : (
          <div className="space-y-2">
            {supplier.recentIncidents.map((r) => (
              <Link
                key={r.id}
                to="/exceptions/$exceptionId"
                params={{ exceptionId: r.id }}
                className="flex items-center justify-between rounded-md border border-border px-3 py-2 text-sm hover:bg-accent/40 transition-colors"
              >
                <div>
                  <span className="font-medium">{r.type}</span>
                  <span className="ml-2 text-xs text-muted-foreground">{r.date}</span>
                </div>
                <SeverityBadge severity={r.severity} />
              </Link>
            ))}
          </div>
        )}
      </section>
    </AppShell>
  );
}
