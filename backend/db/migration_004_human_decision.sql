-- Migration 004: Human-in-the-loop decision tracking
-- Run:  psql -p 5433 scs_db -f db/migration_004_human_decision.sql

ALTER TABLE exceptions
    ADD COLUMN IF NOT EXISTS human_decision TEXT,        -- 'Approved' | 'Rejected' | NULL
    ADD COLUMN IF NOT EXISTS human_decision_note TEXT,
    ADD COLUMN IF NOT EXISTS human_decided_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS human_decided_by TEXT;
