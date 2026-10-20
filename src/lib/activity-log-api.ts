import { API_BASE, relativeTime } from "./backend-api";

// The backend returns whatever is stored in audit_log.step, so this is a plain
// string. Known names (Detected, Retrieved, Recommended, Decided, Reported,
// Notified, Note, SLA Breach, etc.) are styled in activity-log.tsx, and
// anything else falls back to a generic badge.
export type ActivityStep = string;

export interface ActivityLogEntry {
  step: ActivityStep;
  timestamp: string;
  summary: string;
  exceptionId: string;
  exceptionType: string;
  severity: "Low" | "Medium" | "High";
  supplierName: string;
}

export async function fetchActivityLog(limit = 50): Promise<ActivityLogEntry[]> {
  const res = await fetch(`${API_BASE}/api/activity-log?limit=${limit}`);
  if (!res.ok) throw new Error("Failed to load activity log");
  return res.json();
}

export { relativeTime };