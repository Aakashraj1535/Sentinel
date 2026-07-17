import { API_BASE } from "./backend-api";

export type RiskTrend = "Rising" | "Stable" | "Improving";
export type PredictedRiskLevel = "Low" | "Medium" | "High";

export interface PredictiveRiskForecast {
  supplierId: string;
  supplierName: string;
  trend: RiskTrend;
  recentIncidentCount: number;
  priorIncidentCount: number;
  predictedRiskLevel: PredictedRiskLevel;
  explanation: string;
  computedAt: string;
}

export interface RefreshPredictiveRiskResponse {
  suppliers_analyzed: number;
  results: PredictiveRiskForecast[];
}

export async function fetchPredictiveRisk(): Promise<PredictiveRiskForecast[]> {
  const res = await fetch(`${API_BASE}/api/predictive-risk`);
  if (!res.ok) throw new Error("Failed to load predictive risk forecast");
  return res.json();
}

export async function refreshPredictiveRisk(): Promise<RefreshPredictiveRiskResponse> {
  const res = await fetch(`${API_BASE}/api/predictive-risk/refresh`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Failed to refresh predictive risk forecast");
  return res.json();
}
