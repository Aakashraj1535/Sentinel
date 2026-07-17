import { API_BASE } from "./backend-api";

export interface SystemHealth {
  ollamaReachable: boolean;
  databaseReachable: boolean;
  lastExceptionDetectedAt: string | null;
}

export async function fetchSystemHealth(): Promise<SystemHealth> {
  const res = await fetch(`${API_BASE}/api/system-health`);
  if (!res.ok) throw new Error("Failed to load system health");
  return res.json();
}
