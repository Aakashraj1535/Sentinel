import { TrendingUp, TrendingDown, Minus, HelpCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import type { TrendDirection } from "@/lib/insights-api";

const base =
  "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium border";

export function TrendBadge({ direction }: { direction: TrendDirection }) {
  const map: Record<TrendDirection, string> = {
    Improving:
      "bg-[color-mix(in_oklab,var(--success)_15%,transparent)] text-[color-mix(in_oklab,var(--success)_50%,black)] border-[color-mix(in_oklab,var(--success)_30%,transparent)]",
    Declining:
      "bg-[color-mix(in_oklab,var(--danger)_15%,transparent)] text-[color-mix(in_oklab,var(--danger)_60%,black)] border-[color-mix(in_oklab,var(--danger)_35%,transparent)]",
    Stable:
      "bg-muted text-muted-foreground border-border",
    "Insufficient data":
      "bg-muted/50 text-muted-foreground border-dashed border-border",
  };
  const Icon =
    direction === "Improving" ? TrendingUp :
    direction === "Declining" ? TrendingDown :
    direction === "Stable" ? Minus : HelpCircle;

  return (
    <span className={cn(base, map[direction])} title={
      direction === "Insufficient data"
        ? "Not enough delivered orders in each comparison window yet to call a trend."
        : `Comparing the most recent half of the tracked period against the half before it.`
    }>
      <Icon className="h-3 w-3" />
      {direction}
    </span>
  );
}
