import { API_BASE, relativeTime } from "./backend-api";

export type ActivityStep =
  | "Detected"
  | "Retrieved"
  | "Recommended"
  | "Decided"
  | "Reported"
  | "Notified";

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
