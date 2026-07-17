import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { AlertTriangle, Bell, CheckCircle2 } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import {
  fetchNotifications,
  relativeTime,
  type NotificationRecord,
} from "@/lib/backend-api";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/notifications")({
  head: () => ({
    meta: [
      { title: "Notifications — Sentinel" },
      {
        name: "description",
        content:
          "Recent escalation and resolution notifications from the exception management pipeline.",
      },
    ],
  }),
  component: NotificationsPage,
});

function NotificationsPage() {
  const [items, setItems] = useState<NotificationRecord[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchNotifications()
      .then(setItems)
      .catch(() => setError("Unable to load notifications."));
  }, []);

  return (
    <AppShell>
      <div className="mb-6 flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-md bg-primary/10 text-primary">
          <Bell className="h-4 w-4" />
        </div>
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Notifications</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">
            Escalations and resolutions dispatched to Procurement and Warehouse teams.
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
          <Bell className="h-6 w-6 mx-auto text-muted-foreground mb-2" />
          <p className="text-sm text-muted-foreground">No notifications yet.</p>
        </div>
      )}

      {items && items.length > 0 && (
        <ul className="space-y-2">
          {items.map((n) => (
            <li key={n.id}>
              <Link
                to="/exceptions/$exceptionId"
                params={{ exceptionId: n.exceptionId }}
                className="flex items-start gap-3 rounded-lg border border-border bg-surface p-4 hover:bg-accent/40 transition-colors"
              >
                <NotificationIcon type={n.type} />
                <div className="flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2 mb-1">
                    <TypeTag type={n.type} />
                    <AudienceTag audience={n.audience} />
                    <span className="font-mono text-[11px] text-muted-foreground">
                      {n.exceptionId}
                    </span>
                    <span className="ml-auto text-[11px] text-muted-foreground tabular-nums">
                      {relativeTime(n.timestamp)}
                    </span>
                  </div>
                  <p className="text-sm text-foreground leading-relaxed">
                    {n.message}
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

function NotificationIcon({ type }: { type: NotificationRecord["type"] }) {
  if (type === "escalation") {
    return (
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-[color-mix(in_oklab,var(--warning)_18%,transparent)] text-warning">
        <AlertTriangle className="h-4 w-4" />
      </div>
    );
  }
  return (
    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-[color-mix(in_oklab,var(--success)_18%,transparent)] text-success">
      <CheckCircle2 className="h-4 w-4" />
    </div>
  );
}

function TypeTag({ type }: { type: NotificationRecord["type"] }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium uppercase tracking-wide",
        type === "escalation"
          ? "bg-[color-mix(in_oklab,var(--warning)_18%,transparent)] text-[color-mix(in_oklab,var(--warning)_55%,black)] border-[color-mix(in_oklab,var(--warning)_35%,transparent)]"
          : "bg-[color-mix(in_oklab,var(--success)_15%,transparent)] text-[color-mix(in_oklab,var(--success)_50%,black)] border-[color-mix(in_oklab,var(--success)_30%,transparent)]",
      )}
    >
      {type}
    </span>
  );
}

function AudienceTag({ audience }: { audience: NotificationRecord["audience"] }) {
  return (
    <span className="inline-flex items-center rounded-full border border-border bg-muted px-2 py-0.5 text-[11px] font-medium text-muted-foreground">
      {audience}
    </span>
  );
}
