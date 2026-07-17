import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import {
  ArrowLeft,
  Loader2,
  MessageSquare,
  RefreshCw,
  Send,
  Sparkles,
} from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { DocStatusBadge } from "@/components/knowledge-base/DocStatusBadge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  askDocument,
  CHAT_LANGUAGES,
  fetchDocument,
  formatDate,
  formatFileSize,
  reindexDocument,
  type ChatLanguage,
  type DocumentRecord,
} from "@/lib/kb-api";

export const Route = createFileRoute("/knowledge-base/$documentId")({
  head: () => ({
    meta: [
      { title: "Document — Knowledge Base — Sentinel" },
      {
        name: "description",
        content:
          "Document metadata, AI-generated summary, and conversational Q&A against the indexed knowledge base.",
      },
    ],
  }),
  component: DocumentDetailPage,
});

const EXAMPLE_QUESTIONS = [
  "What are the delivery terms?",
  "What is the payment condition?",
  "What happens if shipment is delayed?",
  "Summarize this document.",
];

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  sources?: number;
}

function DocumentDetailPage() {
  const { documentId } = Route.useParams();
  const [doc, setDoc] = useState<DocumentRecord | null>(null);
  const [loading, setLoading] = useState(true);
  const [reindexing, setReindexing] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [language, setLanguage] = useState<ChatLanguage>("English");
  const chatEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    setLoading(true);
    fetchDocument(documentId)
      .then(setDoc)
      .catch((e) =>
        toast.error(e instanceof Error ? e.message : "Failed to load document"),
      )
      .finally(() => setLoading(false));
  }, [documentId]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, asking]);

  const handleReindex = async () => {
    setReindexing(true);
    try {
      await reindexDocument(documentId);
      toast.success("Reindex started");
      // Refresh status after a moment
      setTimeout(() => {
        fetchDocument(documentId).then(setDoc).catch(() => {});
      }, 1000);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Reindex failed");
    } finally {
      setReindexing(false);
    }
  };

  const submitQuestion = async (q: string) => {
    const text = q.trim();
    if (!text || asking) return;
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setQuestion("");
    setAsking(true);
    try {
      const res = await askDocument(documentId, text, language);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: res.answer, sources: res.sources_used },
      ]);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed to get answer";
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Error: ${msg}` },
      ]);
      toast.error(msg);
    } finally {
      setAsking(false);
    }
  };

  return (
    <AppShell>
      <div className="mb-6">
        <Link
          to="/knowledge-base"
          className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Knowledge Base
        </Link>
      </div>

      {loading || !doc ? (
        <div className="space-y-4">
          <Skeleton className="h-8 w-1/2" />
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      ) : (
        <>
          <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
            <div className="min-w-0">
              <h1 className="text-2xl font-semibold tracking-tight text-foreground break-all">
                {doc.fileName}
              </h1>
              <div className="mt-2 flex items-center gap-3">
                <DocStatusBadge status={doc.status} />
                <span className="text-xs text-muted-foreground">
                  {doc.docType}
                </span>
              </div>
            </div>
            <Button
              variant="outline"
              onClick={handleReindex}
              disabled={reindexing}
            >
              {reindexing ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <RefreshCw className="h-4 w-4" />
              )}
              Reindex
            </Button>
          </div>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3 mb-8">
            <div className="rounded-lg border border-border bg-surface p-5 lg:col-span-1">
              <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-4">
                Metadata
              </h2>
              <dl className="space-y-3 text-sm">
                <MetaRow label="Document ID" value={<span className="font-mono text-xs">{doc.id}</span>} />
                <MetaRow label="Type" value={doc.docType} />
                <MetaRow label="Supplier" value={doc.supplierId ?? "—"} />
                <MetaRow label="Uploaded by" value={doc.uploadedBy} />
                <MetaRow label="Uploaded at" value={formatDate(doc.uploadedAt)} />
                <MetaRow label="File size" value={formatFileSize(doc.fileSizeBytes)} />
                <MetaRow label="Chunks" value={doc.chunkCount.toString()} />
                <MetaRow
                  label="Last indexed"
                  value={doc.lastIndexedAt ? formatDate(doc.lastIndexedAt) : "—"}
                />
              </dl>
            </div>

            <div className="rounded-lg border border-border bg-surface p-5 lg:col-span-2">
              <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3 flex items-center gap-2">
                <Sparkles className="h-3.5 w-3.5" />
                AI summary
              </h2>
              {doc.status === "Failed" ? (
                <p className="text-sm text-danger">
                  {doc.errorMessage ?? "Indexing failed."}
                </p>
              ) : doc.status === "Processing" || !doc.summary ? (
                <p className="text-sm text-muted-foreground italic">
                  Summary not yet available.
                </p>
              ) : (
                <p className="text-sm leading-relaxed text-foreground whitespace-pre-wrap">
                  {doc.summary}
                </p>
              )}
            </div>
          </div>

          <div className="rounded-lg border border-border bg-surface">
            <div className="border-b border-border px-5 py-4 flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2 className="text-sm font-semibold text-foreground flex items-center gap-2">
                  <MessageSquare className="h-4 w-4 text-primary" />
                  Ask this document
                </h2>
                <p className="mt-1 text-xs text-muted-foreground">
                  Chat with the indexed content of this document. Answers may take
                  5–20 seconds.
                </p>
              </div>
              <div className="flex flex-col items-end gap-1">
                <label className="flex items-center gap-2 text-xs text-muted-foreground">
                  Answer in
                  <select
                    value={language}
                    onChange={(e) => setLanguage(e.target.value as ChatLanguage)}
                    disabled={asking}
                    className="rounded-md border border-input bg-background px-2 py-1 text-xs text-foreground outline-none focus:ring-2 focus:ring-ring/40 disabled:opacity-60"
                  >
                    {CHAT_LANGUAGES.map((l) => (
                      <option key={l} value={l}>
                        {l}
                      </option>
                    ))}
                  </select>
                </label>
                <span className="text-[10px] text-muted-foreground/80">
                  Answer quality in non-English languages may vary
                </span>
              </div>
            </div>


            <div className="px-5 py-4">
              <div className="mb-3 flex flex-wrap gap-2">
                {EXAMPLE_QUESTIONS.map((q) => (
                  <button
                    key={q}
                    onClick={() => submitQuestion(q)}
                    disabled={asking || doc.status !== "Indexed"}
                    className="rounded-full border border-border bg-background px-3 py-1 text-xs text-muted-foreground hover:bg-accent hover:text-foreground disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {q}
                  </button>
                ))}
              </div>

              <div className="min-h-[120px] max-h-[420px] overflow-y-auto space-y-3 rounded-md bg-background/50 p-3 border border-border">
                {messages.length === 0 && !asking ? (
                  <p className="text-center text-xs text-muted-foreground py-8">
                    No questions yet. Try an example or type your own below.
                  </p>
                ) : (
                  messages.map((m, i) => (
                    <div
                      key={i}
                      className={
                        m.role === "user"
                          ? "flex justify-end"
                          : "flex justify-start"
                      }
                    >
                      <div
                        className={
                          m.role === "user"
                            ? "max-w-[80%] rounded-lg bg-primary text-primary-foreground px-3 py-2 text-sm"
                            : "max-w-[85%] rounded-lg bg-muted text-foreground px-3 py-2 text-sm"
                        }
                      >
                        <p className="whitespace-pre-wrap">{m.content}</p>
                        {m.role === "assistant" && typeof m.sources === "number" && (
                          <p className="mt-1 text-[10px] uppercase tracking-wider text-muted-foreground">
                            {m.sources} source{m.sources === 1 ? "" : "s"} used
                          </p>
                        )}
                      </div>
                    </div>
                  ))
                )}
                {asking && (
                  <div className="flex justify-start">
                    <div className="rounded-lg bg-muted px-3 py-2 text-sm text-muted-foreground flex items-center gap-2">
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      Thinking…
                    </div>
                  </div>
                )}
                <div ref={chatEndRef} />
              </div>

              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  submitQuestion(question);
                }}
                className="mt-3 flex items-center gap-2"
              >
                <Input
                  placeholder={
                    doc.status === "Indexed"
                      ? "Ask a question about this document…"
                      : "Document must finish indexing before you can ask questions"
                  }
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  disabled={asking || doc.status !== "Indexed"}
                />
                <Button
                  type="submit"
                  disabled={asking || !question.trim() || doc.status !== "Indexed"}
                >
                  <Send className="h-4 w-4" />
                  Send
                </Button>
              </form>
            </div>
          </div>
        </>
      )}
    </AppShell>
  );
}

function MetaRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-3">
      <dt className="text-xs uppercase tracking-wider text-muted-foreground">
        {label}
      </dt>
      <dd className="text-sm text-foreground text-right">{value}</dd>
    </div>
  );
}
