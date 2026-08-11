export const KB_API_BASE = "http://localhost:8080";

export type DocType = "Contract" | "SOP" | "Purchase Order" | "Invoice" | "Policy";
export type DocStatus = "Processing" | "Indexed" | "Failed";

export interface DocumentRecord {
  id: string;
  fileName: string;
  docType: DocType;
  supplierId: string | null;
  uploadedBy: string;
  uploadedAt: string;
  fileSizeBytes: number;
  status: DocStatus;
  chunkCount: number;
  summary: string | null;
  lastIndexedAt: string | null;
  errorMessage: string | null;
}

export interface DocumentsSummary {
  totalDocuments: number;
  contracts: number;
  sops: number;
  indexedDocuments: number;
  recentlyUploaded: number;
}

export interface SupplierOption {
  id: string;
  name: string;
}

export async function fetchDocumentsSummary(): Promise<DocumentsSummary> {
  const res = await fetch(`${KB_API_BASE}/api/documents/summary`);
  if (!res.ok) throw new Error("Failed to load summary");
  return res.json();
}

export async function fetchDocuments(docType?: DocType): Promise<DocumentRecord[]> {
  const url = new URL(`${KB_API_BASE}/api/documents`);
  if (docType) url.searchParams.set("doc_type", docType);
  const res = await fetch(url.toString());
  if (!res.ok) throw new Error("Failed to load documents");
  return res.json();
}

export async function fetchDocument(id: string): Promise<DocumentRecord> {
  const res = await fetch(`${KB_API_BASE}/api/documents/${id}`);
  if (!res.ok) throw new Error("Failed to load document");
  return res.json();
}

export async function deleteDocument(id: string): Promise<void> {
  const res = await fetch(`${KB_API_BASE}/api/documents/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to delete");
}

export async function reindexDocument(id: string): Promise<void> {
  const res = await fetch(`${KB_API_BASE}/api/documents/${id}/reindex`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to reindex");
}

export async function uploadDocument(input: {
  file: File;
  docType: DocType;
  supplierId?: string;
  uploadedBy: string;
}): Promise<DocumentRecord> {
  const form = new FormData();
  form.append("file", input.file);
  form.append("doc_type", input.docType);
  if (input.supplierId) form.append("supplier_id", input.supplierId);
  form.append("uploaded_by", input.uploadedBy);
  const res = await fetch(`${KB_API_BASE}/api/documents/upload`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) throw new Error("Upload failed");
  return res.json();
}

export const CHAT_LANGUAGES = [
  "English",
  "Tamil",
  "Hindi",
  "Spanish",
  "French",
  "German",
  "Mandarin",
  "Japanese",
] as const;
export type ChatLanguage = (typeof CHAT_LANGUAGES)[number];

export async function askDocument(
  id: string,
  question: string,
  language: ChatLanguage = "English",
): Promise<{ answer: string; sources_used: number }> {
  const body = new URLSearchParams({ question, language });
  const res = await fetch(`${KB_API_BASE}/api/documents/${id}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  if (!res.ok) throw new Error("Chat failed");
  return res.json();
}

export async function fetchKbSuppliers(): Promise<SupplierOption[]> {
  const res = await fetch(`${KB_API_BASE}/api/suppliers`);
  if (!res.ok) throw new Error("Failed to load suppliers");
  return res.json();
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export const DOC_TYPES: DocType[] = ["Contract", "SOP", "Purchase Order", "Invoice", "Policy"];
