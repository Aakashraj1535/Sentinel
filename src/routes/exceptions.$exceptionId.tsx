import { createFileRoute, Link, notFound } from "@tanstack/react-router";
import { Printer } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { RecommendationCard } from "@/components/RecommendationCard";
import { CompareRecommendations } from "@/components/CompareRecommendationsDialog";
import { SeverityBadge, StatusBadge, SlaBadge } from "@/components/StatusBadges";
import { AuditTimeline } from "@/components/AuditTimeline";
import { HumanReviewPanel } from "@/components/HumanReviewPanel";
import { RootCauseCategoryTag } from "@/components/RootCauseCategoryTag";
import { PrintableIncidentReport } from "@/components/PrintableIncidentReport";
import { getException, type ExceptionRecord } from "@/lib/mock-api";
import type { ExceptionWithReview } from "@/lib/human-review-api";
import {
  ArrowLeft,
  BookOpen,
  CheckCircle2,
  FileText,
  History,
  ShieldAlert,
  Sparkles,
} from "lucide-react";

export const Route = createFileRoute("/exceptions/$exceptionId")({
  loader: async ({ params }) => {
    const ex = await getException(params.exceptionId);
    if (!ex) throw notFound();
    return { exception: ex };
  },
  component: ExceptionDetailPage,
  notFoundComponent: () => (
    <AppShell>
      <div className="rounded-lg border border-border bg-surface p-10 text-center">
        <h2 className="text-lg font-semibold">Exception not found</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          The requested exception ID doesn't exist.
        </p>
        <Link
          to="/"
          className="mt-4 inline-flex items-center gap-1.5 text-sm text-primary hover:underline"
        >
          <ArrowLeft className="h-4 w-4" /> Back to dashboard
        </Link>
      </div>
    </AppShell>
  ),
});

function fmt(iso: string) {
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function ExceptionDetailPage() {
  const { exception } = Route.useLoaderData() as {
    exception: ExceptionWithReview;
  };
  return (
    <AppShell>
      <PrintableIncidentReport exception={exception} />
      <div className="print:hidden">
        <Link
          to="/"
          className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground mb-4"
        >
          <ArrowLeft className="h-4 w-4" /> Back to dashboard
        </Link>

        <Header ex={exception} />

        <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2 space-y-6">
            <Panel title="Recommended actions" icon={Sparkles}>
              {exception.recommendations.length >= 2 && (
                <div className="mb-3 flex justify-end">
                  <CompareRecommendations recommendations={exception.recommendations} />
                </div>
              )}
              <div className="space-y-3">
                {exception.recommendations.map((r, i) => (
                  <RecommendationCard key={r.id} rec={r} primary={i === 0} />
                ))}
              </div>
            </Panel>

            <Panel title="Retrieved knowledge" icon={BookOpen}>
              <p className="text-xs text-muted-foreground mb-3">
                Context documents surfaced by the retrieval layer and used to
                generate the recommendations above.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {exception.knowledge.map((k) => (
                  <div
                    key={k.id}
                    className="rounded-md border border-border bg-background/60 p-3"
                  >
                    <div className="flex items-center gap-2 mb-1.5">
                      <span className="font-mono text-[11px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
                        {k.label}
                      </span>
                      <span className="text-[11px] uppercase tracking-wider text-muted-foreground">
                        {k.kind}
                      </span>
                    </div>
                    <p className="text-sm text-foreground leading-relaxed">
                      {k.excerpt}
                    </p>
                  </div>
                ))}
              </div>
            </Panel>
          </div>

          <div className="space-y-6">
            <EscalationCard ex={exception} />

            <HumanReviewPanel exception={exception} />

            <Panel title="Root cause" icon={FileText}>
              <div className="mb-3">
                <RootCauseCategoryTag
                  exceptionId={exception.id}
                  category={exception.rootCauseCategory}
                  source={exception.rootCauseCategorySource}
                />
              </div>
              <p className="text-sm leading-relaxed text-foreground">
                {exception.rootCause}
              </p>
            </Panel>

            <Panel title="Timeline" icon={History}>
              <AuditTimeline steps={exception.audit} />
            </Panel>
          </div>
        </div>
      </div>
    </AppShell>
  );
}

function Header({ ex }: { ex: ExceptionRecord }) {
  return (
    <div className="rounded-lg border border-border bg-surface p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs text-muted-foreground font-mono">
            {ex.id}
          </div>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">
            {ex.supplier}
          </h1>
          <div className="mt-1 text-sm text-muted-foreground">
            {ex.type} · Detected {fmt(ex.detectedAt)}
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <SeverityBadge severity={ex.severity} />
          <StatusBadge status={ex.status} />
          {ex.slaStatus && (
            <SlaBadge status={ex.slaStatus} hoursRemaining={ex.slaHoursRemaining} />
          )}
          <button
            onClick={() => window.print()}
            className="ml-1 inline-flex items-center gap-1.5 rounded-md border border-border bg-background px-3 py-1.5 text-xs font-medium hover:bg-accent"
          >
            <Printer className="h-3.5 w-3.5" />
            Print Report
          </button>
        </div>
      </div>
    </div>
  );
}

function EscalationCard({ ex }: { ex: ExceptionRecord }) {
  if (ex.autoResolved) {
    return (
      <div className="rounded-lg border border-border bg-surface p-5">
        <div className="flex items-center gap-2 text-success">
          <CheckCircle2 className="h-4 w-4" />
          <span className="text-sm font-semibold">Auto-resolved</span>
        </div>
        <p className="mt-2 text-sm text-muted-foreground">
          System executed the top recommendation without human intervention.
          High confidence and within policy thresholds.
        </p>
      </div>
    );
  }
  if (ex.status === "Escalated") {
    return (
      <div className="rounded-lg border border-[color-mix(in_oklab,var(--danger)_30%,transparent)] bg-[color-mix(in_oklab,var(--danger)_8%,transparent)] p-5">
        <div className="flex items-center gap-2 text-danger">
          <ShieldAlert className="h-4 w-4" />
          <span className="text-sm font-semibold">Flagged for human review</span>
        </div>
        <p className="mt-2 text-sm text-foreground">
          {ex.escalationReason ?? "Escalated per policy."}
        </p>
      </div>
    );
  }
  return (
    <div className="rounded-lg border border-[color-mix(in_oklab,var(--info)_30%,transparent)] bg-[color-mix(in_oklab,var(--info)_8%,transparent)] p-5">
      <div className="flex items-center gap-2 text-info">
        <ShieldAlert className="h-4 w-4" />
        <span className="text-sm font-semibold">Awaiting decision</span>
      </div>
      <p className="mt-2 text-sm text-muted-foreground">
        Recommendations generated. Approve an action to proceed.
      </p>
    </div>
  );
}

function Panel({
  title,
  icon: Icon,
  children,
}: {
  title: string;
  icon: React.ComponentType<{ className?: string }>;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-lg border border-border bg-surface p-5">
      <h2 className="flex items-center gap-2 text-sm font-semibold text-foreground mb-4">
        <Icon className="h-4 w-4 text-muted-foreground" />
        {title}
      </h2>
      {children}
    </section>
  );
}
