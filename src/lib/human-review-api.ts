import { API_BASE } from "./backend-api";
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
  author = "Demo User",
): Promise<{ added: boolean }> {
  const body = new URLSearchParams({ note, author });
  const res = await fetch(`${API_BASE}/api/exceptions/${id}/note`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  if (!res.ok) throw new Error("Failed to add note");
  return res.json();
}

export async function submitExceptionDecision(
  id: string,
  decision: HumanDecision,
  note = "",
  decidedBy = "Demo User",
): Promise<ExceptionWithReview> {
  const body = new URLSearchParams({
    decision,
    note,
    decided_by: decidedBy,
  });
  const res = await fetch(`${API_BASE}/api/exceptions/${id}/decision`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  if (!res.ok) throw new Error("Failed to submit decision");
  return res.json();
}
