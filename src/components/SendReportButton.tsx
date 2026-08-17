import { useState } from "react";
import { Loader2, Lock, Send } from "lucide-react";
import { toast } from "sonner";
import { sendExecutiveReportNow } from "@/lib/backend-api";
import { useHasRole } from "@/hooks/use-role";
import { cn } from "@/lib/utils";

/**
 * Sends the executive digest (exception counts, SLA health, at-risk
 * suppliers, AI calibration) immediately on whatever channels are
 * configured, instead of waiting for the weekly schedule -- exists so
 * this feature is demo-able on demand.
 */
export function SendReportButton() {
  const [loading, setLoading] = useState(false);
  const canSend = useHasRole("Admin");

  async function handleClick() {
    setLoading(true);
    try {
      const result = await sendExecutiveReportNow();
      if (!result.emailSent && !result.slackSent) {
        toast(
          "Report generated, but no channels are configured — set SCS_REPORT_RECIPIENT/SCS_NOTIFY_TO or SCS_SLACK_WEBHOOK_URL to actually deliver it.",
        );
      } else {
        const channels = [
          result.emailSent && "email",
          result.slackSent && "Slack",
        ]
          .filter(Boolean)
          .join(" and ");
        toast.success(`Executive digest sent via ${channels}.`);
      }
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to send report. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  if (!canSend) {
    return (
      <div
        className="flex items-center gap-1.5 rounded-md border border-border px-3.5 py-2 text-sm text-muted-foreground"
        title="Sign in as Admin to send the executive digest."
      >
        <Lock className="h-3.5 w-3.5" />
        Send Report Now
      </div>
    );
  }

  return (
    <button
      onClick={handleClick}
      disabled={loading}
      className={cn(
        "inline-flex items-center gap-2 rounded-md border border-border bg-surface px-3.5 py-2 text-sm font-medium text-foreground shadow-sm transition-colors",
        "hover:bg-accent disabled:opacity-70 disabled:cursor-not-allowed",
      )}
    >
      {loading ? (
        <Loader2 className="h-4 w-4 animate-spin" />
      ) : (
        <Send className="h-4 w-4" />
      )}
      {loading ? "Sending..." : "Send Report Now"}
    </button>
  );
}
