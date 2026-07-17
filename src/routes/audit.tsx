import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { AuditTrailList } from "@/components/AuditTrailList";
import { getExceptions, type ExceptionRecord } from "@/lib/mock-api";

export const Route = createFileRoute("/audit")({
  head: () => ({
    meta: [
      { title: "Audit Trail — Sentinel" },
      {
        name: "description",
        content:
          "Chronological record of detected supply chain exceptions, retrieved context, recommendations, and decisions.",
      },
    ],
  }),
  component: AuditPage,
});

function AuditPage() {
  const [items, setItems] = useState<ExceptionRecord[]>([]);
  useEffect(() => {
    getExceptions().then((all) =>
      setItems(
        [...all].sort(
          (a, b) =>
            new Date(b.detectedAt).getTime() - new Date(a.detectedAt).getTime(),
        ),
      ),
    );
  }, []);

  return (
    <AppShell>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight">Audit Trail</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Every exception's full lifecycle — what was detected, retrieved,
          recommended, and decided.
        </p>
      </div>

      <div className="mb-4 flex items-center gap-4 text-xs text-muted-foreground">
        <span>{items.length} incidents</span>
        <span>·</span>
        <span>{items.filter((i) => i.autoResolved).length} auto-resolved</span>
        <span>·</span>
        <span>
          {items.filter((i) => i.status === "Escalated").length} escalated
        </span>
      </div>

      <AuditTrailList items={items} />
    </AppShell>
  );
}
