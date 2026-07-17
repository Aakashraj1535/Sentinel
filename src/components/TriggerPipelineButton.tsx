import { useState } from "react";
import { Loader2, PlayCircle } from "lucide-react";
import { toast } from "sonner";
import { runPipeline } from "@/lib/backend-api";
import { cn } from "@/lib/utils";

export function TriggerPipelineButton({ onComplete }: { onComplete?: () => void }) {
  const [loading, setLoading] = useState(false);

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
      toast.error("Failed to run exception pipeline. Please try again.");
    } finally {
      setLoading(false);
    }
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
