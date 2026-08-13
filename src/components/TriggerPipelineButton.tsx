import { useState } from "react";
import { Loader2, Lock, PlayCircle } from "lucide-react";
import { toast } from "sonner";
import { runPipeline } from "@/lib/backend-api";
import { hasRole } from "@/lib/auth";
import { cn } from "@/lib/utils";

export function TriggerPipelineButton({ onComplete }: { onComplete?: () => void }) {
  const [loading, setLoading] = useState(false);
  const canRun = hasRole("Procurement Manager");

  async function handleClick() {
    setLoading(true);
    try {
      const result = await runPipeline();
      if (result.processed > 0) {
        toast.success(
          `Detected and resolved ${result.processed} new exception${result.processed === 1 ? "" : "s"}`,
        );
      } else {
        toast("No new exceptions found.");
      }
      onComplete?.();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to run exception pipeline. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  if (!canRun) {
    return (
      <div
        className="flex items-center gap-1.5 rounded-md border border-border px-3.5 py-2 text-sm text-muted-foreground"
        title="Sign in as a Procurement Manager or Admin to run the pipeline."
      >
        <Lock className="h-3.5 w-3.5" />
        Check for New Exceptions
      </div>
    );
  }

  return (
    <div className="flex items-center gap-3">
      {loading && (
        <span className="text-xs text-muted-foreground hidden sm:inline">
          Analyzing new exceptions...
        </span>
      )}
      <button
        onClick={handleClick}
        disabled={loading}
        className={cn(
          "inline-flex items-center gap-2 rounded-md bg-primary px-3.5 py-2 text-sm font-medium text-primary-foreground shadow-sm transition-colors",
          "hover:opacity-90 disabled:opacity-70 disabled:cursor-not-allowed",
        )}
      >
        {loading ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <PlayCircle className="h-4 w-4" />
        )}
        {loading ? "Analyzing..." : "Check for New Exceptions"}
      </button>
    </div>
  );
}
