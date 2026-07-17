import { cn } from "@/lib/utils";
import type { ConfidenceLevel } from "@/lib/mock-api";

const COLOR: Record<ConfidenceLevel, string> = {
  High: "var(--success)",
  Medium: "var(--warning)",
  Low: "var(--danger)",
};

export function ConfidenceGauge({
  pct,
  level,
  size = 56,
  className,
}: {
  pct: number;
  level: ConfidenceLevel;
  size?: number;
  className?: string;
}) {
  const stroke = 5;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const clamped = Math.max(0, Math.min(100, pct));
  const dash = (clamped / 100) * c;

  return (
    <div
      className={cn("relative inline-flex items-center justify-center", className)}
      style={{ width: size, height: size }}
      role="img"
      aria-label={`Confidence ${pct}% (${level})`}
    >
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="var(--border)"
          strokeWidth={stroke}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={COLOR[level]}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${dash} ${c - dash}`}
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <span className="text-xs font-semibold tabular-nums">{Math.round(clamped)}%</span>
      </div>
    </div>
  );
}
