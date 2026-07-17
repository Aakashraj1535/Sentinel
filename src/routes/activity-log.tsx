import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import {
  Bot,
  CheckCircle2,
  BookOpen,
  Search,
  Sparkles,
  Send,
} from "lucide-react";
import { AppShell } from "@/components/AppShell";
import {
  fetchActivityLog,
  relativeTime,
  type ActivityLogEntry,
  type ActivityStep,
} from "@/lib/activity-log-api";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/activity-log")({
  head: () => ({
    meta: [
      { title: "Agent Activity Log — Sentinel" },
      {
        name: "description",
        content:
          "Recent agent activity across the exception management pipeline.",
      },
    ],
  }),
  component: ActivityLogPage,
});

function ActivityLogPage() {
  const [items, setItems] = useState<ActivityLogEntry[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchActivityLog(50)
      .then(setItems)
      .catch(() => setError("Unable to load agent activity log."));
  }, []);

  return (
    <AppShell>
      <div className="mb-6 flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-md bg-primary/10 text-primary">
          <Bot className="h-4 w-4" />
        </div>
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">
            Agent Activity Log
          </h1>
          <p className="mt-0.5 text-sm text-muted-foreground">
            Recent agent actions across detection, retrieval, recommendation,
            decision, and reporting.
          </p>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-border bg-surface p-6 text-sm text-muted-foreground">
          {error}
        </div>
      )}

      {!error && items === null && (
        <div className="space-y-2">
          {[0, 1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-16 rounded-lg border border-border bg-surface animate-pulse"
            />
          ))}
        </div>
      )}

      {items && items.length === 0 && (
        <div className="rounded-lg border border-border bg-surface p-10 text-center">
          <Bot className="h-6 w-6 mx-auto text-muted-foreground mb-2" />
          <p className="text-sm text-muted-foreground">
            No agent activity recorded yet.
          </p>
        </div>
      )}

      {items && items.length > 0 && (
        <ul className="space-y-2">
          {items.map((entry, index) => (
            <li key={`${entry.exceptionId}-${entry.timestamp}-${index}`}>
              <Link
                to="/exceptions/$exceptionId"
                params={{ exceptionId: entry.exceptionId }}
                className="flex items-start gap-3 rounded-lg border border-border bg-surface p-4 hover:bg-accent/40 transition-colors"
              >
                <StepIcon step={entry.step} />
                <div className="flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2 mb-1">
                    <StepTag step={entry.step} />
                    <SeverityDot severity={entry.severity} />
                    <span className="text-xs text-foreground">
                      {entry.supplierName}
                    </span>
                    <span className="font-mono text-[11px] text-muted-foreground">
                      {entry.exceptionId}
                    </span>
                    <span className="ml-auto text-[11px] text-muted-foreground tabular-nums">
                      {relativeTime(entry.timestamp)}
                    </span>
                  </div>
                  <p className="text-sm text-foreground leading-relaxed">
                    {entry.summary}
                  </p>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    {entry.exceptionType}
                  </p>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </AppShell>
  );
}

const stepConfig: Record<
  ActivityStep,
  { icon: React.ComponentType<{ className?: string }>; label: string; tone: string }
> = {
  Detected: {
    icon: Search,
    label: "Detected",
    tone: "info",
  },
  Retrieved: {
    icon: BookOpen,
    label: "Retrieved",
    tone: "warning",
  },
  Recommended: {
    icon: Sparkles,
    label: "Recommended",
    tone: "primary",
  },
  Decided: {
    icon: CheckCircle2,
    label: "Decided",
    tone: "success",
  },
  Reported: {
    icon: Send,
    label: "Reported",
    tone: "muted",
  },
};

function StepIcon({ step }: { step: ActivityStep }) {
  const { icon: Icon, tone } = stepConfig[step];
  const toneClasses: Record<string, string> = {
    info: "bg-[color-mix(in_oklab,var(--info)_18%,transparent)] text-info",
    warning:
      "bg-[color-mix(in_oklab,var(--warning)_18%,transparent)] text-warning",
    primary:
      "bg-[color-mix(in_oklab,var(--primary)_18%,transparent)] text-primary",
    success:
      "bg-[color-mix(in_oklab,var(--success)_18%,transparent)] text-success",
    muted:
      "bg-[color-mix(in_oklab,var(--muted-foreground)_18%,transparent)] text-muted-foreground",
  };
  return (
    <div
      className={cn(
        "flex h-8 w-8 shrink-0 items-center justify-center rounded-md",
        toneClasses[tone],
      )}
    >
      <Icon className="h-4 w-4" />
    </div>
  );
}

function StepTag({ step }: { step: ActivityStep }) {
  const { label, tone } = stepConfig[step];
  const toneClasses: Record<string, string> = {
    info: "bg-[color-mix(in_oklab,var(--info)_15%,transparent)] text-[color-mix(in_oklab,var(--info)_55%,black)] border-[color-mix(in_oklab,var(--info)_35%,transparent)]",
    warning:
      "bg-[color-mix(in_oklab,var(--warning)_18%,transparent)] text-[color-mix(in_oklab,var(--warning)_55%,black)] border-[color-mix(in_oklab,var(--warning)_35%,transparent)]",
    primary:
      "bg-[color-mix(in_oklab,var(--primary)_15%,transparent)] text-[color-mix(in_oklab,var(--primary)_55%,black)] border-[color-mix(in_oklab,var(--primary)_35%,transparent)]",
    success:
      "bg-[color-mix(in_oklab,var(--success)_15%,transparent)] text-[color-mix(in_oklab,var(--success)_50%,black)] border-[color-mix(in_oklab,var(--success)_30%,transparent)]",
    muted:
      "bg-muted text-muted-foreground border-border",
  };
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium uppercase tracking-wide",
        toneClasses[tone],
      )}
    >
      {label}
    </span>
  );
}

function SeverityDot({
  severity,
}: {
  severity: ActivityLogEntry["severity"];
}) {
  const colorClass =
    severity === "High"
      ? "bg-danger"
      : severity === "Medium"
        ? "bg-warning"
        : "bg-success";
  return (
    <span className="inline-flex items-center gap-1.5 text-[11px] text-muted-foreground">
      <span className={cn("h-1.5 w-1.5 rounded-full", colorClass)} />
      {severity}
    </span>
  );
}
