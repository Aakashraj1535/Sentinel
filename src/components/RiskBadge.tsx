import { cn } from "@/lib/utils";

export type RiskLevel = "Low" | "Medium" | "High";

const base =
  "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium border";

export function RiskBadge({ level }: { level: RiskLevel }) {
  const map: Record<RiskLevel, string> = {
    Low: "bg-[color-mix(in_oklab,var(--success)_15%,transparent)] text-[color-mix(in_oklab,var(--success)_50%,black)] border-[color-mix(in_oklab,var(--success)_30%,transparent)]",
    Medium:
      "bg-[color-mix(in_oklab,var(--warning)_18%,transparent)] text-[color-mix(in_oklab,var(--warning)_55%,black)] border-[color-mix(in_oklab,var(--warning)_35%,transparent)]",
    High: "bg-[color-mix(in_oklab,var(--danger)_15%,transparent)] text-[color-mix(in_oklab,var(--danger)_60%,black)] border-[color-mix(in_oklab,var(--danger)_35%,transparent)]",
  };
  return (
    <span className={cn(base, map[level])}>
      <span
        className={cn(
          "h-1.5 w-1.5 rounded-full",
          level === "Low" && "bg-success",
          level === "Medium" && "bg-warning",
          level === "High" && "bg-danger",
        )}
      />
      {level} risk
    </span>
  );
}
