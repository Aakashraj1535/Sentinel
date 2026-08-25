import { API_BASE, roleHeaders } from "./backend-api";
import { getDisplayName } from "./auth";
import type { ExceptionRecord } from "./mock-api";

export type HumanDecision = "Approved" | "Rejected";

export interface HumanReviewFields {
  humanDecision?: HumanDecision | null;
  humanDecisionNote?: string | null;
  humanDecidedAt?: string | null;
  humanDecidedBy?: string | null;
}

export type ExceptionWithReview = ExceptionRecord & HumanReviewFields;

export async function addExceptionNote(
  id: string,
  note: string,
  author = getDisplayName(),
): Promise<{ added: boolean }> {
  const body = new URLSearchParams({ note, author });
  const res = await fetch(`${API_BASE}/api/exceptions/${id}/note`, {
    method: "POST",
    headers: roleHeaders({ "Content-Type": "application/x-www-form-urlencoded" }),
    body,
  });
  if (res.status === 403) throw new Error("You don't have permission to add notes.");
  if (!res.ok) throw new Error("Failed to add note");
  return res.json();
}

export async function submitExceptionDecision(
  id: string,
  decision: HumanDecision,
  note = "",
  decidedBy = getDisplayName(),
): Promise<ExceptionWithReview> {
  const body = new URLSearchParams({
    decision,
    note,
    decided_by: decidedBy,
  });
  const res = await fetch(`${API_BASE}/api/exceptions/${id}/decision`, {
    method: "POST",
    headers: roleHeaders({ "Content-Type": "application/x-www-form-urlencoded" }),
    body,
  });
  if (res.status === 403) throw new Error("You don't have permission to approve or reject exceptions.");
  if (!res.ok) throw new Error("Failed to submit decision");
  return res.json();
}

export async function setRootCauseCategory(
  id: string,
  category: string,
): Promise<{ exceptionId: string; rootCauseCategory: string }> {
  const body = new URLSearchParams({ category });
  const res = await fetch(`${API_BASE}/api/exceptions/${id}/root-cause-category`, {
    method: "POST",
    headers: roleHeaders({ "Content-Type": "application/x-www-form-urlencoded" }),
    body,
  });
  if (res.status === 403) throw new Error("You don't have permission to tag root causes.");
  if (!res.ok) throw new Error("Failed to set root cause category");
  return res.json();
}

export interface FinancialImpactEstimateResult {
  exception_id: string;
  estimated_impact: number | null;
  breakdown: {
    orderValue: number;
    severity: string;
    severityPct: number;
    slaBreached: boolean;
    slaBreachAddOnPct: number;
    totalPct: number;
    estimatedImpact: number;
  } | null;
  explanation: string;
}

export async function recomputeFinancialImpact(
  id: string,
): Promise<FinancialImpactEstimateResult> {
  const res = await fetch(`${API_BASE}/api/exceptions/${id}/estimate-financial-impact`, {
    method: "POST",
    headers: roleHeaders(),
  });
  if (res.status === 403) throw new Error("You don't have permission to recompute financial impact.");
  if (!res.ok) throw new Error("Failed to recompute financial impact");
  return res.json();
}
