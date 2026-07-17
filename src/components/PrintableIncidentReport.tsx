import type { ExceptionRecord } from "@/lib/mock-api";
import type { ExceptionWithReview } from "@/lib/human-review-api";

function fmt(iso: string) {
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: "long",
    timeStyle: "short",
  });
}

/**
 * Print-only formal incident report. Hidden on screen, visible in print.
 * Paired with `.no-print` on the screen UI so window.print() renders a
 * clean, chrome-free document users can save as PDF.
 */
export function PrintableIncidentReport({
  exception,
}: {
  exception: ExceptionWithReview | ExceptionRecord;
}) {
  const ex = exception as ExceptionWithReview;
  return (
    <div className="print-only hidden print:block text-black">
      <header className="border-b-2 border-black pb-4 mb-6">
        <div className="flex items-baseline justify-between">
          <div>
            <div className="text-[11px] uppercase tracking-widest text-neutral-600">
              Sentinel · Supply Chain Exception Report
            </div>
            <h1 className="mt-1 text-2xl font-bold">{ex.id}</h1>
          </div>
          <div className="text-right text-[11px]">
            <div className="uppercase tracking-widest text-neutral-600">
              Generated
            </div>
            <div className="tabular-nums">{fmt(new Date().toISOString())}</div>
          </div>
        </div>
      </header>

      <section className="mb-6">
        <h2 className="text-sm font-bold uppercase tracking-wider mb-2">
          Summary
        </h2>
        <table className="w-full text-sm">
          <tbody>
            <PrintRow label="Supplier" value={`${ex.supplier} (${ex.supplierId})`} />
            <PrintRow label="Exception type" value={ex.type} />
            <PrintRow label="Severity" value={ex.severity} />
            <PrintRow label="Status" value={ex.status} />
            <PrintRow label="Detected" value={fmt(ex.detectedAt)} />
            <PrintRow
              label="Auto-resolved"
              value={ex.autoResolved ? "Yes" : "No"}
            />
            {ex.humanDecision && (
              <PrintRow
                label="Human decision"
                value={`${ex.humanDecision} by ${ex.humanDecidedBy ?? "—"}${
                  ex.humanDecidedAt ? ` on ${fmt(ex.humanDecidedAt)}` : ""
                }`}
              />
            )}
          </tbody>
        </table>
      </section>

      <section className="mb-6">
        <h2 className="text-sm font-bold uppercase tracking-wider mb-2">
          Root Cause
        </h2>
        <p className="text-sm leading-relaxed">{ex.rootCause}</p>
        {ex.escalationReason && (
          <>
            <h3 className="mt-3 text-xs font-bold uppercase tracking-wider">
              Escalation reason
            </h3>
            <p className="text-sm leading-relaxed">{ex.escalationReason}</p>
          </>
        )}
      </section>

      <section className="mb-6">
        <h2 className="text-sm font-bold uppercase tracking-wider mb-2">
          Recommended Actions
        </h2>
        <ol className="space-y-3">
          {ex.recommendations.map((r) => (
            <li key={r.id} className="border border-neutral-400 p-3">
              <div className="flex items-baseline justify-between gap-3">
                <div className="font-semibold">
                  #{r.rank} · {r.confidence} confidence ({r.confidencePct}%)
                </div>
              </div>
              <p className="mt-1 text-sm">{r.action}</p>
              <div className="mt-2 grid grid-cols-3 gap-3 text-xs">
                <div>
                  <div className="uppercase tracking-wider text-neutral-600">
                    Est. cost
                  </div>
                  <div className="font-medium">{r.estimatedCost}</div>
                </div>
                <div>
                  <div className="uppercase tracking-wider text-neutral-600">
                    ETA
                  </div>
                  <div className="font-medium">{r.estimatedDelivery}</div>
                </div>
                <div>
                  <div className="uppercase tracking-wider text-neutral-600">
                    Customer impact
                  </div>
                  <div className="font-medium">{r.customerImpact}</div>
                </div>
              </div>
            </li>
          ))}
        </ol>
      </section>

      <section className="mb-6">
        <h2 className="text-sm font-bold uppercase tracking-wider mb-2">
          Audit Trail
        </h2>
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="border-b border-neutral-500 text-left">
              <th className="py-1 pr-3 font-semibold">Step</th>
              <th className="py-1 pr-3 font-semibold">Timestamp</th>
              <th className="py-1 font-semibold">Summary</th>
            </tr>
          </thead>
          <tbody>
            {ex.audit.map((s, i) => (
              <tr key={i} className="border-b border-neutral-300 align-top">
                <td className="py-1 pr-3 font-medium">{s.step}</td>
                <td className="py-1 pr-3 tabular-nums whitespace-nowrap">
                  {fmt(s.timestamp)}
                </td>
                <td className="py-1">{s.summary}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <footer className="mt-8 border-t border-neutral-400 pt-3 text-[10px] uppercase tracking-widest text-neutral-600">
        Sentinel Ops Console · Confidential · Internal use only
      </footer>
    </div>
  );
}

function PrintRow({ label, value }: { label: string; value: string }) {
  return (
    <tr className="border-b border-neutral-300">
      <td className="py-1 pr-4 text-neutral-600 uppercase text-[11px] tracking-wider w-40">
        {label}
      </td>
      <td className="py-1 font-medium">{value}</td>
    </tr>
  );
}
