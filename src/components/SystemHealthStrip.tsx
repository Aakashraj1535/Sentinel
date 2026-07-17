import { useEffect, useState } from "react";
import { fetchSystemHealth, type SystemHealth } from "@/lib/system-health-api";
import { relativeTime } from "@/lib/backend-api";
import { cn } from "@/lib/utils";

function Dot({ ok }: { ok: boolean | null }) {
  return (
    <span
      className={cn(
        "h-2 w-2 rounded-full",
        ok === null && "bg-muted-foreground/40",
        ok === true && "bg-success",
        ok === false && "bg-danger",
      )}
    />
  );
}

export function SystemHealthStrip() {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const h = await fetchSystemHealth();
        if (!cancelled) {
          setHealth(h);
          setError(false);
        }
      } catch {
        if (!cancelled) setError(true);
      }
    }
    load();
    const id = setInterval(load, 30_000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  return (
    <div className="flex flex-wrap items-center gap-x-5 gap-y-2 rounded-md border border-border bg-surface px-4 py-2 text-xs">
      <div className="flex items-center gap-2">
        <Dot ok={error ? false : health?.ollamaReachable ?? null} />
        <span className="text-muted-foreground">Local LLM</span>
        <span className="font-medium">
          {error || health?.ollamaReachable === false
            ? "Offline"
            : health?.ollamaReachable
              ? "Online"
              : "…"}
        </span>
      </div>
      <div className="h-3 w-px bg-border" />
      <div className="flex items-center gap-2">
        <Dot ok={error ? false : health?.databaseReachable ?? null} />
        <span className="text-muted-foreground">Database</span>
        <span className="font-medium">
          {error || health?.databaseReachable === false
            ? "Offline"
            : health?.databaseReachable
              ? "Connected"
              : "…"}
        </span>
      </div>
      <div className="h-3 w-px bg-border" />
      <div className="flex items-center gap-2">
        <span className="text-muted-foreground">Last Detection</span>
        <span className="font-medium tabular-nums">
          {health?.lastExceptionDetectedAt
            ? relativeTime(health.lastExceptionDetectedAt)
            : "No data yet"}
        </span>
      </div>
    </div>
  );
}
