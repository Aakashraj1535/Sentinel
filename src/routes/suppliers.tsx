import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Lock, Plus } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { SeverityBadge } from "@/components/StatusBadges";
import { RiskBadge } from "@/components/RiskBadge";
import { PredictiveRiskPanel } from "@/components/PredictiveRiskPanel";
import { AddSupplierDialog } from "@/components/AddSupplierDialog";
import { Button } from "@/components/ui/button";
import { getSuppliers, type Supplier } from "@/lib/mock-api";
import { hasRole } from "@/lib/auth";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/suppliers")({
  head: () => ({
    meta: [
      { title: "Suppliers — Sentinel" },
      {
        name: "description",
        content:
          "Supplier performance overview: on-time delivery rate, incident count, and recent incident history.",
      },
    ],
  }),
  component: SuppliersPage,
});

function rateTone(rate: number) {
  if (rate >= 95) return "text-success";
  if (rate >= 88) return "text-foreground";
  return "text-danger";
}

function SuppliersPage() {
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [addOpen, setAddOpen] = useState(false);
  const canAddSupplier = hasRole("Admin");
  useEffect(() => {
    getSuppliers().then(setSuppliers);
  }, []);

  return (
    <AppShell>
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Suppliers</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Performance overview and incident history across the supplier network.
          </p>
        </div>
        {canAddSupplier ? (
          <Button onClick={() => setAddOpen(true)}>
            <Plus className="h-4 w-4" />
            Add supplier
          </Button>
        ) : (
          <Button variant="outline" disabled title="Sign in as Admin to add suppliers.">
            <Lock className="h-4 w-4" />
            Add supplier
          </Button>
        )}
      </div>

      <AddSupplierDialog
        open={addOpen}
        onOpenChange={setAddOpen}
        onAdded={(s) => setSuppliers((prev) => [s, ...prev])}
      />


      <div className="overflow-hidden rounded-lg border border-border bg-surface">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-muted/60 text-xs uppercase tracking-wide text-muted-foreground">
              <tr>
                <th className="px-4 py-3 text-left font-medium">Supplier</th>
                <th className="px-4 py-3 text-left font-medium">Risk</th>
                <th className="px-4 py-3 text-left font-medium">Region</th>
                <th className="px-4 py-3 text-right font-medium">
                  On-time rate
                </th>
                <th className="px-4 py-3 text-right font-medium">
                  Total incidents
                </th>
                <th className="px-4 py-3 text-left font-medium">
                  Recent incidents
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {suppliers.map((s) => (
                <tr key={s.id} className="hover:bg-accent/40 transition-colors">
                  <td className="px-4 py-4">
                    <div className="font-medium">{s.name}</div>
                    <div className="font-mono text-xs text-muted-foreground">
                      {s.id}
                    </div>
                  </td>
                  <td className="px-4 py-4">
                    <RiskBadge level={s.riskLevel} />
                  </td>
                  <td className="px-4 py-4 text-muted-foreground">
                    {s.region}
                  </td>
                  <td
                    className={cn(
                      "px-4 py-4 text-right font-semibold tabular-nums",
                      rateTone(s.onTimeRate),
                    )}
                  >
                    {s.onTimeRate.toFixed(1)}%
                  </td>
                  <td className="px-4 py-4 text-right tabular-nums">
                    {s.totalIncidents}
                  </td>
                  <td className="px-4 py-4">
                    <div className="flex flex-wrap gap-2">
                      {s.recentIncidents.map((r) => (
                        <div
                          key={r.id}
                          className="flex items-center gap-1.5 rounded-md border border-border bg-background/60 px-2 py-1 text-xs"
                        >
                          <span className="font-mono text-muted-foreground">
                            {r.id}
                          </span>
                          <span className="text-muted-foreground">
                            {r.type}
                          </span>
                          <SeverityBadge severity={r.severity} />
                        </div>
                      ))}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="mt-6">
        <PredictiveRiskPanel />
      </div>
    </AppShell>
  );
}
