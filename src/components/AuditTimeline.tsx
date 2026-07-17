import type { AuditStep } from "@/lib/mock-api";
import {
  BookOpen,
  CheckCircle2,
  FileEdit,
  FileText,
  Radar,
  Send,
  Sparkles,
} from "lucide-react";
import { cn } from "@/lib/utils";

type StepKey =
  | "Detected"
  | "Retrieved"
  | "Recommended"
  | "Decided"
  | "Reported"
  | "Note";

interface StepStyle {
  icon: React.ComponentType<{ className?: string }>;
  color: string;
  tint: string;
}

const STYLES: Record<StepKey, StepStyle> = {
  Detected: {
    icon: Radar,
    color: "text-info",
    tint: "bg-[color-mix(in_oklab,var(--info)_14%,transparent)] border-[color-mix(in_oklab,var(--info)_35%,transparent)]",
  },
  Retrieved: {
    icon: BookOpen,
    color: "text-primary",
    tint: "bg-[color-mix(in_oklab,var(--primary)_10%,transparent)] border-[color-mix(in_oklab,var(--primary)_30%,transparent)]",
  },
  Recommended: {
    icon: Sparkles,
    color: "text-warning",
    tint: "bg-[color-mix(in_oklab,var(--warning)_18%,transparent)] border-[color-mix(in_oklab,var(--warning)_35%,transparent)]",
  },
  Decided: {
    icon: CheckCircle2,
    color: "text-success",
    tint: "bg-[color-mix(in_oklab,var(--success)_15%,transparent)] border-[color-mix(in_oklab,var(--success)_35%,transparent)]",
  },
  Reported: {
    icon: Send,
    color: "text-info",
    tint: "bg-[color-mix(in_oklab,var(--info)_14%,transparent)] border-[color-mix(in_oklab,var(--info)_30%,transparent)]",
  },
  Note: {
    icon: FileEdit,
    color: "text-muted-foreground",
    tint: "bg-muted border-border",
  },
};

function fmt(iso: string) {
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

export function AuditTimeline({ steps }: { steps: readonly AuditStep[] }) {
  return (
    <ol className="relative space-y-4 pl-8">
      <span
        className="absolute left-[13px] top-1 bottom-1 w-px bg-border"
        aria-hidden
      />
      {steps.map((s, i) => {
        const style = STYLES[s.step as StepKey] ?? {
          icon: FileText,
          color: "text-muted-foreground",
          tint: "bg-muted border-border",
        };
        const Icon = style.icon;
        return (
          <li key={i} className="relative">
            <span
              className={cn(
                "absolute -left-8 top-0 flex h-7 w-7 items-center justify-center rounded-full border",
                style.tint,
              )}
            >
              <Icon className={cn("h-3.5 w-3.5", style.color)} />
            </span>
            <div className="flex items-baseline justify-between gap-2">
              <span className="text-sm font-medium">{s.step}</span>
              <span className="text-[11px] text-muted-foreground tabular-nums">
                {fmt(s.timestamp)}
              </span>
            </div>
            <p className="mt-0.5 text-xs text-muted-foreground leading-relaxed">
              {s.summary}
            </p>
          </li>
        );
      })}
    </ol>
  );
}
