import { Link } from "@tanstack/react-router";
import type { ExceptionRecord } from "@/lib/mock-api";
import { SeverityBadge, StatusBadge, SlaBadge } from "./StatusBadges";

function formatTime(iso: string) {
  const d = new Date(iso);
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function ExceptionTable({ rows }: { rows: ExceptionRecord[] }) {
  return (
    <div className="overflow-hidden rounded-lg border border-border bg-surface">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-muted/60 text-xs uppercase tracking-wide text-muted-foreground">
            <tr>
              <th className="px-4 py-3 text-left font-medium">Exception</th>
              <th className="px-4 py-3 text-left font-medium">Supplier</th>
              <th className="px-4 py-3 text-left font-medium">Type</th>
              <th className="px-4 py-3 text-left font-medium">Severity</th>
              <th className="px-4 py-3 text-left font-medium">Status</th>
              <th className="px-4 py-3 text-left font-medium">SLA</th>
              <th className="px-4 py-3 text-left font-medium">Detected</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {rows.map((r) => (
              <tr
                key={r.id}
                className="group hover:bg-accent/50 transition-colors"
              >
                <td className="px-4 py-3 font-mono text-xs text-foreground">
                  <Link
                    to="/exceptions/$exceptionId"
                    params={{ exceptionId: r.id }}
                    className="hover:text-primary"
                  >
                    {r.id}
                  </Link>
                </td>
                <td className="px-4 py-3">
                  <Link
                    to="/exceptions/$exceptionId"
                    params={{ exceptionId: r.id }}
                    className="font-medium hover:text-primary"
                  >
                    {r.supplier}
                  </Link>
                </td>
                <td className="px-4 py-3 text-muted-foreground">{r.type}</td>
                <td className="px-4 py-3">
                  <SeverityBadge severity={r.severity} />
                </td>
                <td className="px-4 py-3">
                  <StatusBadge status={r.status} />
                </td>
                <td className="px-4 py-3">
                  {r.slaStatus && (
                    <SlaBadge status={r.slaStatus} hoursRemaining={r.slaHoursRemaining} />
                  )}
                </td>
                <td className="px-4 py-3 text-muted-foreground tabular-nums">
                  {formatTime(r.detectedAt)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
