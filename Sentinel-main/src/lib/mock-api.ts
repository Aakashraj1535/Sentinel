// API layer — calling the real FastAPI backend at localhost:8080
// instead of returning hardcoded mock data. All UI components still
// import from this module only, and the function signatures/types
// are unchanged, so no component code needs to change.

const API_BASE = "http://localhost:8080/api";

export type Severity = "Low" | "Medium" | "High";
export type ExceptionStatus = "Active" | "Resolved" | "Escalated";
export type ExceptionType =
  | "Shipment Delay"
  | "Stockout"
  | "Quality Issue"
  | "Customs Hold"
  | "Supplier Outage";
export type ConfidenceLevel = "High" | "Medium" | "Low";

export interface KnowledgeSource {
  id: string;
  label: string; // e.g. "SOP-14", "Incident #187"
  kind: "SOP" | "Contract" | "Incident" | "Policy";
  excerpt: string;
}

export interface Recommendation {
  id: string;
  rank: number;
  action: string;
  estimatedCost: string;
  estimatedDelivery: string;
  customerImpact: "Minimal" | "Moderate" | "Significant";
  confidencePct: number;
  confidence: ConfidenceLevel;
}

export interface AuditStep {
  step: "Detected" | "Retrieved" | "Recommended" | "Decided";
  timestamp: string;
  summary: string;
}

export type SlaStatus = "On Track" | "At Risk" | "Breached" | "Complete";

export interface ExceptionRecord {
  id: string;
  supplier: string;
  supplierId: string;
  type: ExceptionType;
  severity: Severity;
  status: ExceptionStatus;
  detectedAt: string;
  rootCause: string;
  rootCauseCategory?: string | null;
  rootCauseCategorySource?: "auto" | "human" | null;
  autoResolved: boolean;
  escalationReason?: string;
  slaStatus?: SlaStatus;
  slaDeadline?: string;
  slaHoursRemaining?: number;
  estimatedFinancialImpact?: number | null;
  financialImpactBreakdown?: {
    orderValue: number;
    severity: Severity;
    severityPct: number;
    slaBreached: boolean;
    slaBreachAddOnPct: number;
    totalPct: number;
    estimatedImpact: number;
  } | null;
  financialImpactExplanation?: string | null;
  financialImpactComputedAt?: string | null;
  knowledge: KnowledgeSource[];
  recommendations: Recommendation[];
  audit: AuditStep[];
}

export interface Supplier {
  id: string;
  name: string;
  region: string;
  onTimeRate: number; // 0-100
  totalIncidents: number;
  riskLevel: "Low" | "Medium" | "High";
  recentIncidents: { id: string; type: ExceptionType; date: string; severity: Severity }[];
}

// ---- Real API calls to the FastAPI backend ----
// Each function still returns a Promise, matching the original mock
// signatures exactly, so components using these functions are unaffected.

export async function getExceptions(): Promise<ExceptionRecord[]> {
  const res = await fetch(`${API_BASE}/exceptions`);
  if (!res.ok) throw new Error(`Failed to fetch exceptions: ${res.status}`);
  return res.json();
}

export async function getException(id: string): Promise<ExceptionRecord | undefined> {
  const res = await fetch(`${API_BASE}/exceptions/${id}`);
  if (res.status === 404) return undefined;
  if (!res.ok) throw new Error(`Failed to fetch exception ${id}: ${res.status}`);
  return res.json();
}

export async function getResolvedExceptions(): Promise<ExceptionRecord[]> {
  const res = await fetch(`${API_BASE}/exceptions/resolved`);
  if (!res.ok) throw new Error(`Failed to fetch resolved exceptions: ${res.status}`);
  return res.json();
}

export async function getSuppliers(): Promise<Supplier[]> {
  const res = await fetch(`${API_BASE}/suppliers`);
  if (!res.ok) throw new Error(`Failed to fetch suppliers: ${res.status}`);
  return res.json();
}

export interface DashboardSummary {
  activeCount: number;
  resolvedToday: number;
  slaBreachedCount: number;
  slaAtRiskCount: number;
  avgConfidence: number;
  escalationsPending: number;
  totalFinancialImpactAtRisk: number;
}

export async function getDashboardSummary(): Promise<DashboardSummary> {
  const res = await fetch(`${API_BASE}/dashboard-summary`);
  if (!res.ok) throw new Error(`Failed to fetch dashboard summary: ${res.status}`);
  return res.json();
}