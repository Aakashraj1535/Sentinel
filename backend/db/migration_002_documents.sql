-- Migration 002: Knowledge Base document management
-- Run:  psql -p 5433 scs_db -f db/migration_002_documents.sql

CREATE TABLE IF NOT EXISTS documents (
    id              TEXT PRIMARY KEY,          -- e.g. 'DOC-8f3a1c'
    file_name       TEXT NOT NULL,
    doc_type        TEXT NOT NULL,             -- 'Contract' | 'SOP' | 'Purchase Order' | 'Invoice' | 'Policy'
    supplier_id     TEXT REFERENCES suppliers(id),   -- nullable, not all docs are supplier-specific
    uploaded_by     TEXT NOT NULL DEFAULT 'Demo User',
    uploaded_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    file_size_bytes BIGINT NOT NULL,
    storage_path    TEXT NOT NULL,             -- where the raw file lives on disk
    status          TEXT NOT NULL DEFAULT 'Processing',  -- 'Processing' | 'Indexed' | 'Failed'
    chunk_count     INTEGER NOT NULL DEFAULT 0,
    summary         TEXT,                      -- short LLM-generated summary, filled in after indexing
    last_indexed_at TIMESTAMPTZ,
    error_message   TEXT
);

-- Link knowledge_documents chunks back to their source document.
-- (knowledge_documents already exists from Phase 1 — this just adds a
-- nullable reference so uploaded-document chunks can be traced back
-- and re-indexed/deleted cleanly, while synthetic SOPs/contracts/incidents
-- from Phase 1 remain unaffected, with document_id left NULL for those.)
ALTER TABLE knowledge_documents
    ADD COLUMN IF NOT EXISTS document_id TEXT REFERENCES documents(id);
