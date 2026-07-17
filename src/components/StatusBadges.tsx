import { cn } from "@/lib/utils";
import type {
  ConfidenceLevel,
  ExceptionStatus,
  Severity,
} from "@/lib/mock-api";

const base =
  "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium border";

export function SeverityBadge({ severity }: { severity: Severity }) {
  const map: Record<Severity, string> = {
    Low: "bg-muted text-muted-foreground border-border",
    Medium:
      "bg-[color-mix(in_oklab,var(--warning)_18%,transparent)] text-[color-mix(in_oklab,var(--warning)_55%,black)] border-[color-mix(in_oklab,var(--warning)_35%,transparent)]",
    High: "bg-[color-mix(in_oklab,var(--danger)_15%,transparent)] text-[color-mix(in_oklab,var(--danger)_60%,black)] border-[color-mix(in_oklab,var(--danger)_35%,transparent)]",
  };
  return (
    <span className={cn(base, map[severity])}>
      <span
        className={cn(
          "h-1.5 w-1.5 rounded-full",
          severity === "Low" && "bg-muted-foreground",
          severity === "Medium" && "bg-warning",
          severity === "High" && "bg-danger",
        )}
      />
      {severity}
    </span>
  );
}

export function StatusBadge({ status }: { status: ExceptionStatus }) {
  const map: Record<ExceptionStatus, string> = {
    Active:
      "bg-[color-mix(in_oklab,var(--info)_14%,transparent)] text-[color-mix(in_oklab,var(--info)_55%,black)] border-[color-mix(in_oklab,var(--info)_30%,transparent)]",
    Resolved:
      "bg-[color-mix(in_oklab,var(--success)_15%,transparent)] text-[color-mix(in_oklab,var(--success)_50%,black)] border-[color-mix(in_oklab,var(--success)_30%,transparent)]",
    Escalated:
      "bg-[color-mix(in_oklab,var(--danger)_15%,transparent)] text-[color-mix(in_oklab,var(--danger)_60%,black)] border-[color-mix(in_oklab,var(--danger)_35%,transparent)]",
  };
  return <span className={cn(base, map[status])}>{status}</span>;
}

export function ConfidenceBadge({
  level,
  pct,
}: {
  level: ConfidenceLevel;
  pct?: number;
}) {
  const map: Record<ConfidenceLevel, string> = {
    High: "bg-[color-mix(in_oklab,var(--success)_15%,transparent)] text-[color-mix(in_oklab,var(--success)_50%,black)] border-[color-mix(in_oklab,var(--success)_30%,transparent)]",
    Medium:
      "bg-[color-mix(in_oklab,var(--warning)_18%,transparent)] text-[color-mix(in_oklab,var(--warning)_55%,black)] border-[color-mix(in_oklab,var(--warning)_35%,transparent)]",
    Low: "bg-[color-mix(in_oklab,var(--danger)_14%,transparent)] text-[color-mix(in_oklab,var(--danger)_60%,black)] border-[color-mix(in_oklab,var(--danger)_35%,transparent)]",
  };
  return (
    <span className={cn(base, map[level])}>
      {level}
      {typeof pct === "number" && (
        <span className="tabular-nums opacity-80">· {pct}%</span>
      )}
    </span>
  );
}
