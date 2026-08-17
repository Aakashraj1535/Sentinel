import { cn } from "@/lib/utils";
import type {
  ConfidenceLevel,
  ExceptionStatus,
  Severity,
  SlaStatus,
} from "@/lib/mock-api";
import { Clock, AlertTriangle, CheckCircle2 } from "lucide-react";

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

export function SlaBadge({
  status,
  hoursRemaining,
}: {
  status: SlaStatus;
  hoursRemaining?: number;
}) {
  if (status === "Complete") return null; // nothing worth showing once done

  const map: Record<Exclude<SlaStatus, "Complete">, string> = {
    "On Track":
      "bg-[color-mix(in_oklab,var(--success)_15%,transparent)] text-[color-mix(in_oklab,var(--success)_50%,black)] border-[color-mix(in_oklab,var(--success)_30%,transparent)]",
    "At Risk":
      "bg-[color-mix(in_oklab,var(--warning)_18%,transparent)] text-[color-mix(in_oklab,var(--warning)_55%,black)] border-[color-mix(in_oklab,var(--warning)_35%,transparent)]",
    Breached:
      "bg-[color-mix(in_oklab,var(--danger)_15%,transparent)] text-[color-mix(in_oklab,var(--danger)_60%,black)] border-[color-mix(in_oklab,var(--danger)_35%,transparent)]",
  };
  const Icon = status === "Breached" ? AlertTriangle : status === "At Risk" ? Clock : CheckCircle2;

  const label =
    status === "Breached" && typeof hoursRemaining === "number"
      ? `SLA breached · ${Math.abs(hoursRemaining)}h overdue`
      : status === "On Track" && typeof hoursRemaining === "number"
        ? `${hoursRemaining}h left`
        : status;

  return (
    <span
      className={cn(base, map[status as Exclude<SlaStatus, "Complete">])}
      title={
        status === "Breached"
          ? "This exception has exceeded its response SLA."
          : status === "At Risk"
            ? "This exception is approaching its SLA deadline."
            : "This exception is within its SLA window."
      }
    >
      <Icon className="h-3 w-3" />
      {label}
    </span>
  );
}
