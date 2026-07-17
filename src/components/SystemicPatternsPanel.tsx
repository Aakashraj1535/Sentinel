import { useEffect, useState } from "react";
import { Network, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { fetchSystemicPatterns, type SystemicPattern } from "@/lib/insights-api";
import { Skeleton } from "@/components/ui/skeleton";

export function SystemicPatternsPanel() {
  const [patterns, setPatterns] = useState<SystemicPattern[] | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetchSystemicPatterns()
      .then((p) => {
        if (!cancelled) setPatterns(p);
      })
      .catch((e) => {
        if (!cancelled) {
          toast.error(e instanceof Error ? e.message : "Failed to load patterns");
          setPatterns([]);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <section className="rounded-lg border border-border bg-surface p-5">
      <div className="mb-4 flex items-center gap-2">
        <Network className="h-4 w-4 text-muted-foreground" />
        <h2 className="text-sm font-semibold text-foreground">
          Systemic Pattern Detection
        </h2>
      </div>
      <p className="mb-4 text-xs text-muted-foreground">
        Cross-supplier issues sharing a common root cause. Recomputed on each
        load.
      </p>

      {loading ? (
        <div className="space-y-3">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-24 w-full" />
        </div>
      ) : !patterns || patterns.length === 0 ? (
        <div className="rounded-md border border-dashed border-border bg-background/40 p-6 text-center">
          <p className="text-sm text-muted-foreground">
            No systemic patterns detected — this is checked automatically across
            all suppliers.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          {patterns.map((p, i) => (
            <PatternCard key={i} pattern={p} />
          ))}
        </div>
      )}
    </section>
  );
}

function PatternCard({ pattern }: { pattern: SystemicPattern }) {
  return (
    <div className="rounded-md border border-border bg-background/60 p-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <h3 className="text-sm font-semibold text-foreground">
          {pattern.causeCategory}
        </h3>
        <span className="inline-flex items-center rounded-full border border-[color-mix(in_oklab,var(--warning)_30%,transparent)] bg-[color-mix(in_oklab,var(--warning)_10%,transparent)] px-2 py-0.5 text-[11px] font-medium text-warning">
          {pattern.affectedSupplierCount} suppliers affected
        </span>
      </div>
      <div className="mt-3 flex flex-wrap gap-1.5">
        {pattern.affectedSuppliers.map((s) => (
          <span
            key={s}
            className="rounded-full bg-muted px-2 py-0.5 text-[11px] text-foreground"
          >
            {s}
          </span>
        ))}
      </div>
      <p className="mt-3 text-xs leading-relaxed text-muted-foreground">
        {pattern.explanation}
      </p>
      <div className="mt-2 text-[11px] text-muted-foreground tabular-nums">
        {pattern.totalIncidents} incident{pattern.totalIncidents === 1 ? "" : "s"}
      </div>
    </div>
  );
}
