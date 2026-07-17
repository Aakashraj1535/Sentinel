import { API_BASE } from "./backend-api";

export interface SystemicPattern {
  causeCategory: string;
  affectedSupplierCount: number;
  affectedSuppliers: string[];
  totalIncidents: number;
  exceptionIds: string[];
  explanation: string;
}

export async function fetchSystemicPatterns(): Promise<SystemicPattern[]> {
  const res = await fetch(`${API_BASE}/api/systemic-patterns`);
  if (!res.ok) throw new Error("Failed to load systemic patterns");
  return res.json();
}

export interface CalibrationMetrics {
  totalDecided: number;
  approved: number;
  rejected: number;
  agreementRate: number | null;
  avgConfidenceWhenApproved: number | null;
  avgConfidenceWhenRejected: number | null;
}

export async function fetchCalibration(): Promise<CalibrationMetrics> {
  const res = await fetch(`${API_BASE}/api/analytics/calibration`);
  if (!res.ok) throw new Error("Failed to load calibration metrics");
  return res.json();
}
