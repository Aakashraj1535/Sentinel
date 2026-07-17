import type { Recommendation } from "@/lib/mock-api";
import { ConfidenceBadge } from "./StatusBadges";
import { ConfidenceGauge } from "./ConfidenceGauge";
import { ArrowRight, Clock, DollarSign, Users } from "lucide-react";
import { cn } from "@/lib/utils";

export function RecommendationCard({
  rec,
  primary,
}: {
  rec: Recommendation;
  primary?: boolean;
}) {
  return (
    <div
      className={cn(
        "rounded-lg border bg-surface p-5",
        primary ? "border-primary/40 ring-1 ring-primary/20" : "border-border",
      )}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-2">
          <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary text-primary-foreground text-xs font-semibold">
            {rec.rank}
          </span>
          <span className="text-xs uppercase tracking-wide text-muted-foreground">
            {primary ? "Recommended" : "Alternative"}
          </span>
        </div>
        <div className="flex items-center gap-3">
          <ConfidenceBadge level={rec.confidence} />
          <ConfidenceGauge pct={rec.confidencePct} level={rec.confidence} />
        </div>
      </div>
      <p className="mt-3 text-sm leading-relaxed text-foreground">{rec.action}</p>
      <div className="mt-4 grid grid-cols-3 gap-3 border-t border-border pt-4 text-xs">
        <Metric icon={DollarSign} label="Est. cost" value={rec.estimatedCost} />
        <Metric icon={Clock} label="ETA" value={rec.estimatedDelivery} />
        <Metric icon={Users} label="Customer impact" value={rec.customerImpact} />
      </div>
      {primary && (
        <button className="mt-4 inline-flex items-center gap-1.5 text-xs font-medium text-primary hover:underline">
          Approve action <ArrowRight className="h-3 w-3" />
        </button>
      )}
    </div>
  );
}

function Metric({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
}) {
  return (
    <div>
      <div className="flex items-center gap-1 text-muted-foreground">
        <Icon className="h-3 w-3" />
        <span>{label}</span>
      </div>
      <div className="mt-1 font-medium text-foreground">{value}</div>
    </div>
  );
}
