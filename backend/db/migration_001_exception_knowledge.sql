-- Migration: adds the exception_knowledge table to an already-existing database.
-- Safe to run even if you already ran the full schema.sql — uses IF NOT EXISTS.
-- Run:  psql -p 5433 scs_db -f db/migration_001_exception_knowledge.sql

CREATE TABLE IF NOT EXISTS exception_knowledge (
    id              SERIAL PRIMARY KEY,
    exception_id    TEXT NOT NULL REFERENCES exceptions(id),
    doc_label       TEXT NOT NULL,
    doc_kind        TEXT NOT NULL,
    excerpt         TEXT NOT NULL,
    relevance       TEXT
);
