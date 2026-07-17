import { cn } from "@/lib/utils";
import type { DocStatus } from "@/lib/kb-api";

const base =
  "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium border";

export function DocStatusBadge({ status }: { status: DocStatus }) {
  const map: Record<DocStatus, string> = {
    Indexed:
      "bg-[color-mix(in_oklab,var(--success)_15%,transparent)] text-[color-mix(in_oklab,var(--success)_50%,black)] border-[color-mix(in_oklab,var(--success)_30%,transparent)]",
    Processing:
      "bg-[color-mix(in_oklab,var(--warning)_18%,transparent)] text-[color-mix(in_oklab,var(--warning)_55%,black)] border-[color-mix(in_oklab,var(--warning)_35%,transparent)]",
    Failed:
      "bg-[color-mix(in_oklab,var(--danger)_15%,transparent)] text-[color-mix(in_oklab,var(--danger)_60%,black)] border-[color-mix(in_oklab,var(--danger)_35%,transparent)]",
  };
  const dot: Record<DocStatus, string> = {
    Indexed: "bg-success",
    Processing: "bg-warning animate-pulse",
    Failed: "bg-danger",
  };
  return (
    <span className={cn(base, map[status])}>
      <span className={cn("h-1.5 w-1.5 rounded-full", dot[status])} />
      {status}
    </span>
  );
}
