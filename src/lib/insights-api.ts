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

export interface RootCauseTrendWeek {
  week: string;
  [category: string]: string | number;
}

export interface RootCauseBreakdown {
  overall: Record<string, number>;
  trend: RootCauseTrendWeek[];
  categories: string[];
}

export async function fetchRootCauseBreakdown(): Promise<RootCauseBreakdown> {
  const res = await fetch(`${API_BASE}/api/analytics/root-causes`);
  if (!res.ok) throw new Error("Failed to load root cause breakdown");
  return res.json();
}

export interface SupplierTrendWeek {
  week: string;
  onTimeRate: number;
  orderCount: number;
  onTimeCount: number;
}

export type TrendDirection = "Improving" | "Declining" | "Stable" | "Insufficient data";

export interface SupplierTrend {
  supplierId: string;
  weeklySeries: SupplierTrendWeek[];
  trendDirection: TrendDirection;
  recentOnTimeRate: number;
  priorOnTimeRate: number;
}

export async function fetchSupplierTrend(supplierId: string): Promise<SupplierTrend> {
  const res = await fetch(`${API_BASE}/api/suppliers/${supplierId}/trend`);
  if (!res.ok) throw new Error("Failed to load supplier trend");
  return res.json();
}
