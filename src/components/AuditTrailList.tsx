import { useState } from "react";
import type { ExceptionRecord } from "@/lib/mock-api";
import { SeverityBadge, StatusBadge } from "./StatusBadges";
import { ChevronDown, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

function fmt(iso: string) {
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export function AuditTrailList({ items }: { items: ExceptionRecord[] }) {
  return (
    <div className="space-y-3">
      {items.map((item) => (
        <AuditRow key={item.id} item={item} />
      ))}
    </div>
  );
}

function AuditRow({ item }: { item: ExceptionRecord }) {
  const [open, setOpen] = useState(false);
  const top = item.recommendations[0];
  return (
    <div className="rounded-lg border border-border bg-surface">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center gap-4 px-5 py-4 text-left hover:bg-accent/40 transition-colors"
      >
        {open ? (
          <ChevronDown className="h-4 w-4 text-muted-foreground shrink-0" />
        ) : (
          <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0" />
        )}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 text-sm">
            <span className="font-mono text-xs text-muted-foreground">{item.id}</span>
            <span className="font-medium truncate">{item.supplier}</span>
            <span className="text-muted-foreground">·</span>
            <span className="text-muted-foreground truncate">{item.type}</span>
          </div>
          <div className="mt-1 text-xs text-muted-foreground tabular-nums">
            {fmt(item.detectedAt)}
          </div>
        </div>
        <SeverityBadge severity={item.severity} />
        <StatusBadge status={item.status} />
      </button>
      <div
        className={cn(
          "grid transition-all",
          open ? "grid-rows-[1fr]" : "grid-rows-[0fr]",
        )}
      >
        <div className="overflow-hidden">
          <div className="border-t border-border px-5 py-5 space-y-5">
            <Section title="Detected">
              <p className="text-sm text-foreground">{item.rootCause}</p>
            </Section>
            <Section title="Retrieved">
              <ul className="space-y-1.5 text-sm">
                {item.knowledge.map((k) => (
                  <li key={k.id} className="flex gap-2">
                    <span className="font-mono text-xs px-1.5 py-0.5 rounded bg-muted text-muted-foreground shrink-0">
                      {k.label}
                    </span>
                    <span className="text-muted-foreground">{k.excerpt}</span>
                  </li>
                ))}
              </ul>
            </Section>
            <Section title="Recommended">
              {top && (
                <p className="text-sm text-foreground">
                  <span className="font-medium">Top action ({top.confidencePct}%):</span>{" "}
                  {top.action}
                </p>
              )}
            </Section>
            <Section title="Decision">
              <p className="text-sm text-foreground">
                {item.autoResolved
                  ? "Auto-resolved by system."
                  : item.status === "Escalated"
                    ? `Escalated to human review. Reason: ${item.escalationReason ?? "—"}`
                    : "Pending human decision."}
              </p>
            </Section>
            <Section title="Timeline">
              <ol className="relative border-l border-border pl-4 space-y-3">
                {item.audit.map((s, i) => (
                  <li key={i} className="text-sm">
                    <span className="absolute -left-[5px] mt-1.5 h-2 w-2 rounded-full bg-primary" />
                    <div className="flex items-baseline gap-2">
                      <span className="font-medium">{s.step}</span>
                      <span className="text-xs text-muted-foreground tabular-nums">
                        {fmt(s.timestamp)}
                      </span>
                    </div>
                    <div className="text-muted-foreground">{s.summary}</div>
                  </li>
                ))}
              </ol>
            </Section>
          </div>
        </div>
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="text-[11px] uppercase tracking-wider font-semibold text-muted-foreground mb-2">
        {title}
      </div>
      {children}
    </div>
  );
}
