import { useState } from "react";
import { GitCompare, X } from "lucide-react";
import type { Recommendation } from "@/lib/mock-api";
import { ConfidenceBadge } from "./StatusBadges";
import { cn } from "@/lib/utils";

export function CompareRecommendations({
  recommendations,
}: {
  recommendations: Recommendation[];
}) {
  const [open, setOpen] = useState(false);
  const [selected, setSelected] = useState<string[]>([]);

  if (recommendations.length < 2) return null;

  function toggle(id: string) {
    setSelected((prev) => {
      if (prev.includes(id)) return prev.filter((x) => x !== id);
      if (prev.length >= 2) return [prev[1], id];
      return [...prev, id];
    });
  }

  const picked = selected
    .map((id) => recommendations.find((r) => r.id === id))
    .filter((r): r is Recommendation => Boolean(r));

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="inline-flex items-center gap-1.5 rounded-md border border-border bg-surface px-3 py-1.5 text-xs font-medium text-foreground hover:bg-accent transition-colors"
      >
        <GitCompare className="h-3.5 w-3.5" />
        Compare options
      </button>

      {open && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
          onClick={() => setOpen(false)}
        >
          <div
            className="w-full max-w-3xl max-h-[85vh] overflow-auto rounded-lg border border-border bg-surface shadow-lg"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between border-b border-border px-5 py-4">
              <div>
                <h2 className="text-sm font-semibold flex items-center gap-2">
                  <GitCompare className="h-4 w-4 text-muted-foreground" />
                  Compare recommendations
                </h2>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Select two options to view side-by-side.
                </p>
              </div>
              <button
                onClick={() => setOpen(false)}
                className="text-muted-foreground hover:text-foreground"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="p-5 space-y-4">
              <div className="space-y-2">
                {recommendations.map((r) => {
                  const isChecked = selected.includes(r.id);
                  return (
                    <label
                      key={r.id}
                      className={cn(
                        "flex items-start gap-3 rounded-md border p-3 text-sm cursor-pointer transition-colors",
                        isChecked
                          ? "border-primary/50 bg-primary/5"
                          : "border-border hover:bg-accent/40",
                      )}
                    >
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={() => toggle(r.id)}
                        className="mt-0.5"
                      />
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="flex h-5 w-5 items-center justify-center rounded-full bg-primary text-primary-foreground text-[10px] font-semibold">
                            {r.rank}
                          </span>
                          <ConfidenceBadge
                            level={r.confidence}
                            pct={r.confidencePct}
                          />
                        </div>
                        <div className="text-foreground">{r.action}</div>
                      </div>
                    </label>
                  );
                })}
              </div>

              {picked.length === 2 && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 border-t border-border pt-4">
                  {picked.map((r) => (
                    <div
                      key={r.id}
                      className="rounded-md border border-border bg-background/60 p-4"
                    >
                      <div className="flex items-center gap-2 mb-2">
                        <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary text-primary-foreground text-xs font-semibold">
                          {r.rank}
                        </span>
                        <span className="text-xs uppercase tracking-wide text-muted-foreground">
                          Option {r.rank}
                        </span>
                      </div>
                      <p className="text-sm text-foreground leading-relaxed">
                        {r.action}
                      </p>
                      <dl className="mt-4 space-y-2 text-xs border-t border-border pt-3">
                        <Row label="Estimated cost" value={r.estimatedCost} />
                        <Row label="ETA" value={r.estimatedDelivery} />
                        <Row label="Customer impact" value={r.customerImpact} />
                        <Row
                          label="Confidence"
                          value={`${r.confidencePct}% (${r.confidence})`}
                        />
                      </dl>
                    </div>
                  ))}
                </div>
              )}

              {picked.length < 2 && (
                <div className="rounded-md border border-dashed border-border p-6 text-center text-xs text-muted-foreground">
                  Select {2 - picked.length} more option
                  {2 - picked.length === 1 ? "" : "s"} to see the side-by-side
                  comparison.
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-3">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="font-medium text-foreground text-right">{value}</dd>
    </div>
  );
}
