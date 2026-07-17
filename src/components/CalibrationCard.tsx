import { useEffect, useState } from "react";
import { ThumbsUp } from "lucide-react";
import { fetchCalibration, type CalibrationMetrics } from "@/lib/insights-api";
import { Skeleton } from "@/components/ui/skeleton";

export function CalibrationCard() {
  const [data, setData] = useState<CalibrationMetrics | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    fetchCalibration()
      .then((d) => {
        if (!cancelled) setData(d);
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <section className="rounded-lg border border-border bg-surface p-5">
      <div className="mb-3 flex items-center gap-2">
        <ThumbsUp className="h-4 w-4 text-muted-foreground" />
        <h2 className="text-sm font-semibold text-foreground">
          Recommendation Accuracy
        </h2>
      </div>

      {loading ? (
        <Skeleton className="h-20 w-full" />
      ) : !data || data.totalDecided === 0 ? (
        <p className="text-sm text-muted-foreground">
          No decisions recorded yet — approve or reject an escalated exception
          to start building this metric.
        </p>
      ) : (
        <div>
          <div className="flex items-baseline gap-2">
            <span className="text-4xl font-semibold tabular-nums text-foreground">
              {data.agreementRate !== null
                ? `${Math.round(data.agreementRate)}%`
                : "—"}
            </span>
            <span className="text-xs text-muted-foreground">
              of AI recommendations approved by human reviewers
            </span>
          </div>
          <p className="mt-2 text-xs text-muted-foreground">
            Based on {data.totalDecided} decision
            {data.totalDecided === 1 ? "" : "s"} · {data.approved} approved ·{" "}
            {data.rejected} rejected
          </p>
          {(data.avgConfidenceWhenApproved !== null ||
            data.avgConfidenceWhenRejected !== null) && (
            <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-muted-foreground">
              {data.avgConfidenceWhenApproved !== null && (
                <span>
                  Avg. confidence when approved:{" "}
                  <span className="tabular-nums text-foreground">
                    {Math.round(data.avgConfidenceWhenApproved)}%
                  </span>
                </span>
              )}
              {data.avgConfidenceWhenRejected !== null && (
                <span>
                  Avg. confidence when rejected:{" "}
                  <span className="tabular-nums text-foreground">
                    {Math.round(data.avgConfidenceWhenRejected)}%
                  </span>
                </span>
              )}
            </div>
          )}
        </div>
      )}
    </section>
  );
}
