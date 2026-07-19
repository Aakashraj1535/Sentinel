-- Supply Chain Sentinel — Database Schema
-- Run this once against your local PostgreSQL database.
-- Requires the pgvector extension (installed separately, see README).

CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================
-- SUPPLIERS
-- ============================================================
CREATE TABLE IF NOT EXISTS suppliers (
    id              TEXT PRIMARY KEY,          -- e.g. 'SUP-014'
    name            TEXT NOT NULL,
    region          TEXT NOT NULL,
    on_time_rate    NUMERIC(5,2) NOT NULL DEFAULT 100.00,  -- 0-100
    total_incidents INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- ORDERS / SHIPMENTS  (the operational data agents monitor)
-- ============================================================
CREATE TABLE IF NOT EXISTS orders (
    id                  TEXT PRIMARY KEY,        -- e.g. 'PO-88213'
    supplier_id         TEXT NOT NULL REFERENCES suppliers(id),
    item                TEXT NOT NULL,
    quantity            INTEGER NOT NULL,
    warehouse_id        TEXT NOT NULL,
    expected_delivery   TIMESTAMPTZ NOT NULL,
    actual_delivery     TIMESTAMPTZ,              -- NULL = not yet arrived
    status              TEXT NOT NULL DEFAULT 'pending', -- pending/delivered/delayed
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- KNOWLEDGE DOCUMENTS  (SOPs, contracts, incident logs)
-- Each row is one CHUNK of a document, with its embedding.
-- ============================================================
CREATE TABLE IF NOT EXISTS knowledge_documents (
    id              SERIAL PRIMARY KEY,
    doc_label       TEXT NOT NULL,        -- e.g. 'SOP-14', 'Incident #187'
    doc_kind        TEXT NOT NULL,        -- 'SOP' | 'Contract' | 'Incident' | 'Policy'
    supplier_id     TEXT REFERENCES suppliers(id),   -- nullable: SOPs may be generic
    exception_type  TEXT,                 -- e.g. 'Shipment Delay' (nullable, for routing)
    chunk_text      TEXT NOT NULL,
    embedding       vector(384),          -- from sentence-transformers all-MiniLM-L6-v2
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index for fast similarity search
CREATE INDEX IF NOT EXISTS idx_knowledge_embedding
    ON knowledge_documents USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- ============================================================
-- KNOWLEDGE GRAPH EDGES  (lightweight relationship table)
-- Connects documents to suppliers / exception types / each other
-- ============================================================
CREATE TABLE IF NOT EXISTS knowledge_edges (
    id              SERIAL PRIMARY KEY,
    from_label      TEXT NOT NULL,   -- e.g. 'Incident #187'
    relation        TEXT NOT NULL,   -- e.g. 'caused_by', 'applies_to'
    to_label        TEXT NOT NULL,   -- e.g. 'SUP-014' or 'Shipment Delay'
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- EXCEPTIONS  (detected problems — what the dashboard displays)
-- ============================================================
CREATE TABLE IF NOT EXISTS exceptions (
    id                  TEXT PRIMARY KEY,       -- e.g. 'EX-24817'
    order_id            TEXT REFERENCES orders(id),
    supplier_id         TEXT NOT NULL REFERENCES suppliers(id),
    exception_type      TEXT NOT NULL,          -- 'Shipment Delay' | 'Stockout' | ...
    severity            TEXT NOT NULL,          -- 'Low' | 'Medium' | 'High'
    status               TEXT NOT NULL DEFAULT 'Active', -- Active/Resolved/Escalated
    detected_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    root_cause          TEXT,
    auto_resolved       BOOLEAN NOT NULL DEFAULT false,
    escalation_reason   TEXT
);

-- ============================================================
-- RECOMMENDATIONS  (ranked resolution options per exception)
-- ============================================================
CREATE TABLE IF NOT EXISTS recommendations (
    id                  SERIAL PRIMARY KEY,
    exception_id        TEXT NOT NULL REFERENCES exceptions(id),
    rank                INTEGER NOT NULL,
    action              TEXT NOT NULL,
    estimated_cost      TEXT,
    estimated_delivery  TEXT,
    customer_impact     TEXT,       -- 'Minimal' | 'Moderate' | 'Significant'
    confidence_pct      NUMERIC(5,2),
    confidence_level    TEXT        -- 'High' | 'Medium' | 'Low'
);

-- ============================================================
-- AUDIT TRAIL  (step-by-step log per exception, for the Report agent)
-- ============================================================
CREATE TABLE IF NOT EXISTS audit_log (
    id              SERIAL PRIMARY KEY,
    exception_id    TEXT NOT NULL REFERENCES exceptions(id),
    step            TEXT NOT NULL,     -- 'Detected' | 'Retrieved' | 'Recommended' | 'Decided'
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT now(),
    summary         TEXT NOT NULL
);
