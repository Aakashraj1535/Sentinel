import { createFileRoute, Link } from "@tanstack/react-router";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import {
  BookOpen,
  CheckCircle2,
  Clock,
  Download,
  Eye,
  FileText,
  Files,
  Lock,
  Plus,
  Search,
  Trash2,
} from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { SummaryStat } from "@/components/SummaryStat";
import { DocStatusBadge } from "@/components/knowledge-base/DocStatusBadge";
import { UploadDocumentDialog } from "@/components/knowledge-base/UploadDocumentDialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { cn } from "@/lib/utils";
import { useHasRole } from "@/hooks/use-role";
import {
  DOC_TYPES,
  KB_API_BASE,
  deleteDocument,
  fetchDocument,
  fetchDocuments,
  fetchDocumentsSummary,
  formatDate,
  type DocType,
  type DocumentRecord,
  type DocumentsSummary,
} from "@/lib/kb-api";

export const Route = createFileRoute("/knowledge-base/")({
  head: () => ({
    meta: [
      { title: "Knowledge Base — Sentinel" },
      {
        name: "description",
        content:
          "Central repository of contracts, SOPs, and policies indexed for AI-assisted supply chain decisions.",
      },
    ],
  }),
  component: KnowledgeBasePage,
});

const TABS: { label: string; value: "All" | DocType }[] = [
  { label: "All Documents", value: "All" },
  ...DOC_TYPES.map((t) => ({ label: t === "SOP" ? "SOPs" : `${t}s`, value: t })),
];

function KnowledgeBasePage() {
  const [summary, setSummary] = useState<DocumentsSummary | null>(null);
  const [docs, setDocs] = useState<DocumentRecord[] | null>(null);
  const [tab, setTab] = useState<"All" | DocType>("All");
  const [search, setSearch] = useState("");
  const [uploadOpen, setUploadOpen] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState<DocumentRecord | null>(null);
  const canManageDocs = useHasRole("Admin");
  const pollTimers = useRef<Map<string, number>>(new Map());

  const loadSummary = useCallback(() => {
    fetchDocumentsSummary()
      .then(setSummary)
      .catch(() => setSummary(null));
  }, []);

  const loadDocs = useCallback(() => {
    setDocs(null);
    fetchDocuments(tab === "All" ? undefined : tab)
      .then(setDocs)
      .catch((e) => {
        setDocs([]);
        toast.error(e instanceof Error ? e.message : "Failed to load documents");
      });
  }, [tab]);

  useEffect(() => {
    loadSummary();
  }, [loadSummary]);

  useEffect(() => {
    loadDocs();
  }, [loadDocs]);

  const pollDoc = useCallback((id: string) => {
    const timers = pollTimers.current;
    if (timers.has(id)) return;
    const start = Date.now();
    const interval = window.setInterval(async () => {
      try {
        const doc = await fetchDocument(id);
        setDocs((prev) =>
          prev ? prev.map((d) => (d.id === id ? doc : d)) : prev,
        );
        if (doc.status !== "Processing" || Date.now() - start > 15000) {
          window.clearInterval(interval);
          timers.delete(id);
          if (doc.status === "Indexed") {
            loadSummary();
          }
        }
      } catch {
        window.clearInterval(interval);
        timers.delete(id);
      }
    }, 2000);
    timers.set(id, interval);
  }, [loadSummary]);

  useEffect(() => {
    return () => {
      pollTimers.current.forEach((t) => window.clearInterval(t));
      pollTimers.current.clear();
    };
  }, []);

  const handleUploaded = (docId: string) => {
    loadDocs();
    loadSummary();
    // start polling for status
    setTimeout(() => pollDoc(docId), 500);
  };

  const handleDelete = async (doc: DocumentRecord) => {
    try {
      await deleteDocument(doc.id);
      setDocs((prev) => (prev ? prev.filter((d) => d.id !== doc.id) : prev));
      loadSummary();
      toast.success(`Deleted ${doc.fileName}`);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Delete failed");
    } finally {
      setConfirmDelete(null);
    }
  };

  const handleDownload = (doc: DocumentRecord) => {
    window.location.href = `${KB_API_BASE}/api/documents/${doc.id}/file`;
  };

  const filtered = useMemo(() => {
    if (!docs) return [];
    const q = search.trim().toLowerCase();
    if (!q) return docs;
    return docs.filter((d) => d.fileName.toLowerCase().includes(q));
  }, [docs, search]);

  return (
    <AppShell>
      <div className="mb-8 flex items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">
            Knowledge Base
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Contracts, SOPs, and policies indexed for AI-assisted exception
            resolution.
          </p>
        </div>
        {canManageDocs ? (
          <Button onClick={() => setUploadOpen(true)}>
            <Plus className="h-4 w-4" />
            Upload document
          </Button>
        ) : (
          <Button variant="outline" disabled title="Sign in as Admin to upload documents.">
            <Lock className="h-4 w-4" />
            Upload document
          </Button>
        )}
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5 mb-8">
        <SummaryStat
          label="Total documents"
          value={summary?.totalDocuments ?? "—"}
          icon={<Files className="h-4 w-4" />}
        />
        <SummaryStat
          label="Contracts"
          value={summary?.contracts ?? "—"}
          icon={<FileText className="h-4 w-4" />}
        />
        <SummaryStat
          label="SOPs"
          value={summary?.sops ?? "—"}
          icon={<BookOpen className="h-4 w-4" />}
        />
        <SummaryStat
          label="Indexed"
          value={summary?.indexedDocuments ?? "—"}
          tone="success"
          icon={<CheckCircle2 className="h-4 w-4" />}
        />
        <SummaryStat
          label="Recently uploaded"
          value={summary?.recentlyUploaded ?? "—"}
          hint="Last 7 days"
          icon={<Clock className="h-4 w-4" />}
        />
      </div>

      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap gap-1 rounded-lg border border-border bg-surface p-1">
          {TABS.map((t) => (
            <button
              key={t.value}
              onClick={() => setTab(t.value)}
              className={cn(
                "rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
                tab === t.value
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-accent hover:text-foreground",
              )}
            >
              {t.label}
            </button>
          ))}
        </div>
        <div className="relative w-full sm:w-72">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search file name…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-8"
          />
        </div>
      </div>

      <div className="overflow-hidden rounded-lg border border-border bg-surface">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-muted/60 text-xs uppercase tracking-wide text-muted-foreground">
              <tr>
                <th className="px-4 py-3 text-left font-medium">File name</th>
                <th className="px-4 py-3 text-left font-medium">Type</th>
                <th className="px-4 py-3 text-left font-medium">Supplier</th>
                <th className="px-4 py-3 text-left font-medium">Uploaded</th>
                <th className="px-4 py-3 text-left font-medium">Status</th>
                <th className="px-4 py-3 text-right font-medium">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {docs === null ? (
                Array.from({ length: 4 }).map((_, i) => (
                  <tr key={i}>
                    <td colSpan={6} className="px-4 py-3">
                      <Skeleton className="h-6 w-full" />
                    </td>
                  </tr>
                ))
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-16 text-center">
                    <div className="flex flex-col items-center gap-2 text-muted-foreground">
                      <BookOpen className="h-8 w-8 opacity-50" />
                      <p className="text-sm font-medium text-foreground">
                        {docs.length === 0
                          ? "No documents yet"
                          : "No matching documents"}
                      </p>
                      <p className="text-xs">
                        {docs.length === 0
                          ? "Upload your first document to get started."
                          : "Try a different search or filter."}
                      </p>
                    </div>
                  </td>
                </tr>
              ) : (
                filtered.map((d) => (
                  <tr key={d.id} className="hover:bg-accent/50 transition-colors">
                    <td className="px-4 py-3">
                      <Link
                        to="/knowledge-base/$documentId"
                        params={{ documentId: d.id }}
                        className="flex items-center gap-2 font-medium hover:text-primary"
                      >
                        <FileText className="h-4 w-4 text-muted-foreground" />
                        {d.fileName}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">{d.docType}</td>
                    <td className="px-4 py-3 font-mono text-xs text-muted-foreground">
                      {d.supplierId ?? "—"}
                    </td>
                    <td className="px-4 py-3 text-muted-foreground tabular-nums">
                      {formatDate(d.uploadedAt)}
                    </td>
                    <td className="px-4 py-3">
                      <DocStatusBadge status={d.status} />
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-1">
                        <Link
                          to="/knowledge-base/$documentId"
                          params={{ documentId: d.id }}
                          className="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-foreground"
                          title="View"
                        >
                          <Eye className="h-4 w-4" />
                        </Link>
                        <button
                          onClick={() => handleDownload(d)}
                          className="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-foreground"
                          title="Download"
                        >
                          <Download className="h-4 w-4" />
                        </button>
                        {canManageDocs && (
                          <button
                            onClick={() => setConfirmDelete(d)}
                            className="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-danger/10 hover:text-danger"
                            title="Delete"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      <UploadDocumentDialog
        open={uploadOpen}
        onOpenChange={setUploadOpen}
        onUploaded={handleUploaded}
      />

      <AlertDialog
        open={!!confirmDelete}
        onOpenChange={(v) => !v && setConfirmDelete(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete this document?</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently remove{" "}
              <span className="font-medium text-foreground">
                {confirmDelete?.fileName}
              </span>{" "}
              from the knowledge base. This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => confirmDelete && handleDelete(confirmDelete)}
              className="bg-danger text-danger-foreground hover:opacity-90"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </AppShell>
  );
}
