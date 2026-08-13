import { useState } from "react";
import { CheckCircle2, Loader2, Lock, MessageSquarePlus, ThumbsDown, ThumbsUp, XCircle } from "lucide-react";
import { toast } from "sonner";
import { useRouter } from "@tanstack/react-router";
import {
  addExceptionNote,
  submitExceptionDecision,
  type ExceptionWithReview,
  type HumanDecision,
} from "@/lib/human-review-api";
import { hasRole } from "@/lib/auth";
import { cn } from "@/lib/utils";

function fmt(iso: string) {
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

export function HumanReviewPanel({ exception }: { exception: ExceptionWithReview }) {
  const router = useRouter();
  const [note, setNote] = useState("");
  const [addingNote, setAddingNote] = useState(false);
  const [decisionNote, setDecisionNote] = useState("");
  const [submitting, setSubmitting] = useState<HumanDecision | null>(null);
  const canReview = hasRole("Procurement Manager");

  const alreadyDecided = !!exception.humanDecision;

  async function handleAddNote() {
    if (!note.trim()) {
      toast.error("Please enter a note before submitting.");
      return;
    }
    setAddingNote(true);
    try {
      await addExceptionNote(exception.id, note.trim());
      toast.success("Note added");
      setNote("");
      await router.invalidate();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to add note. Please try again.");
    } finally {
      setAddingNote(false);
    }
  }

  async function handleDecision(decision: HumanDecision) {
    setSubmitting(decision);
    try {
      await submitExceptionDecision(exception.id, decision, decisionNote.trim());
      toast.success("Decision recorded");
      setDecisionNote("");
      await router.invalidate();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to record decision. Please try again.");
    } finally {
      setSubmitting(null);
    }
  }

  if (!canReview) {
    return (
      <section className="rounded-lg border border-border bg-surface p-5 no-print">
        <h2 className="flex items-center gap-2 text-sm font-semibold text-foreground mb-2">
          <MessageSquarePlus className="h-4 w-4 text-muted-foreground" />
          Human Review
        </h2>
        <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <Lock className="h-3.5 w-3.5" />
          Viewing as read-only. Sign in as a Procurement Manager or Admin to
          add notes or approve/reject recommendations.
        </p>
        {alreadyDecided && (
          <div className="mt-4 border-t border-border pt-4">
            <DecisionSummary exception={exception} />
          </div>
        )}
      </section>
    );
  }

  return (
    <section className="rounded-lg border border-border bg-surface p-5 no-print">
      <h2 className="flex items-center gap-2 text-sm font-semibold text-foreground mb-4">
        <MessageSquarePlus className="h-4 w-4 text-muted-foreground" />
        Human Review
      </h2>

      {/* Add note */}
      <div className="space-y-2">
        <label className="text-xs font-medium text-muted-foreground">
          Add note to audit trail
        </label>
        <textarea
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="Describe context, follow-up, or reasoning…"
          rows={2}
          className="w-full resize-none rounded-md border border-input bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring/40"
        />
        <div className="flex justify-end">
          <button
            onClick={handleAddNote}
            disabled={addingNote}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-md border border-border bg-background px-3 py-1.5 text-xs font-medium",
              "hover:bg-accent disabled:opacity-60 disabled:cursor-not-allowed",
            )}
          >
            {addingNote ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <MessageSquarePlus className="h-3.5 w-3.5" />
            )}
            Add Note
          </button>
        </div>
      </div>

      {/* Decision */}
      {(exception.status === "Escalated" || alreadyDecided) && (
        <div className="mt-5 border-t border-border pt-4">
          {alreadyDecided ? (
            <DecisionSummary exception={exception} />
          ) : (
            <div className="space-y-2">
              <label className="text-xs font-medium text-muted-foreground">
                Approve or reject the recommended action
              </label>
              <textarea
                value={decisionNote}
                onChange={(e) => setDecisionNote(e.target.value)}
                placeholder="Optional rationale…"
                rows={2}
                className="w-full resize-none rounded-md border border-input bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring/40"
              />
              <div className="flex flex-wrap gap-2">
                <button
                  onClick={() => handleDecision("Approved")}
                  disabled={submitting !== null}
                  className={cn(
                    "inline-flex flex-1 items-center justify-center gap-1.5 rounded-md bg-success px-3 py-2 text-xs font-semibold text-success-foreground",
                    "hover:opacity-90 disabled:opacity-60 disabled:cursor-not-allowed",
                  )}
                >
                  {submitting === "Approved" ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <ThumbsUp className="h-3.5 w-3.5" />
                  )}
                  Approve
                </button>
                <button
                  onClick={() => handleDecision("Rejected")}
                  disabled={submitting !== null}
                  className={cn(
                    "inline-flex flex-1 items-center justify-center gap-1.5 rounded-md bg-danger px-3 py-2 text-xs font-semibold text-danger-foreground",
                    "hover:opacity-90 disabled:opacity-60 disabled:cursor-not-allowed",
                  )}
                >
                  {submitting === "Rejected" ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <ThumbsDown className="h-3.5 w-3.5" />
                  )}
                  Reject
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </section>
  );
}

function DecisionSummary({ exception }: { exception: ExceptionWithReview }) {
  const approved = exception.humanDecision === "Approved";
  const Icon = approved ? CheckCircle2 : XCircle;
  return (
    <div
      className={cn(
        "rounded-md border p-3",
        approved
          ? "border-[color-mix(in_oklab,var(--success)_30%,transparent)] bg-[color-mix(in_oklab,var(--success)_8%,transparent)]"
          : "border-[color-mix(in_oklab,var(--danger)_30%,transparent)] bg-[color-mix(in_oklab,var(--danger)_8%,transparent)]",
      )}
    >
      <div className={cn("flex items-center gap-2 text-sm font-semibold", approved ? "text-success" : "text-danger")}>
        <Icon className="h-4 w-4" />
        {exception.humanDecision} by {exception.humanDecidedBy ?? "—"}
        {exception.humanDecidedAt && (
          <span className="ml-auto text-[11px] font-normal text-muted-foreground tabular-nums">
            {fmt(exception.humanDecidedAt)}
          </span>
        )}
      </div>
      {exception.humanDecisionNote && (
        <p className="mt-2 text-xs text-foreground leading-relaxed">
          “{exception.humanDecisionNote}”
        </p>
      )}
    </div>
  );
}
