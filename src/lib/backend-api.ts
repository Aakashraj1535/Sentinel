// Real FastAPI backend calls.
export const API_BASE = "http://localhost:8080";

export interface RunPipelineResponse {
  processed: number;
  exception_ids: string[];
}

export async function runPipeline(): Promise<RunPipelineResponse> {
  const res = await fetch(`${API_BASE}/api/run-pipeline`, { method: "POST" });
  if (!res.ok) throw new Error("Pipeline failed");
  return res.json();
}

export interface AnalyticsSummary {
  severityDistribution: { Low: number; Medium: number; High: number };
  typeDistribution: { type: string; count: number }[];
  resolutionTrend: {
    date: string;
    resolved: number;
    escalated: number;
    active: number;
  }[];
  autoResolvedRate: number;
  totalProcessed: number;
}

export async function fetchAnalyticsSummary(): Promise<AnalyticsSummary> {
  const res = await fetch(`${API_BASE}/api/analytics/summary`);
  if (!res.ok) throw new Error("Failed to load analytics");
  return res.json();
}

export type NotificationType = "escalation" | "resolution";
export interface NotificationRecord {
  id: string;
  type: NotificationType;
  audience: "Procurement" | "Warehouse";
  message: string;
  exceptionId: string;
  timestamp: string;
}

export async function fetchNotifications(): Promise<NotificationRecord[]> {
  const res = await fetch(`${API_BASE}/api/notifications`);
  if (!res.ok) throw new Error("Failed to load notifications");
  return res.json();
}

export function relativeTime(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const s = Math.max(1, Math.round(diffMs / 1000));
  if (s < 60) return `${s}s ago`;
  const m = Math.round(s / 60);
  if (m < 60) return `${m} min ago`;
  const h = Math.round(m / 60);
  if (h < 24) return `${h} hour${h === 1 ? "" : "s"} ago`;
  const d = Math.round(h / 24);
  if (d < 30) return `${d} day${d === 1 ? "" : "s"} ago`;
  return new Date(iso).toLocaleDateString();
}
