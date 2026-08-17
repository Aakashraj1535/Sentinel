-- Migration 005: Root Cause Category Tagging
-- Run:  psql -p 5433 scs_db -f db/migration_005_root_cause_category.sql
--
-- Adds a structured category alongside the existing free-text root_cause
-- field, so root causes can be counted and trended over time (e.g. "40%
-- of Q3 delays trace back to customs issues") -- something free text
-- alone can't answer. Auto-populated from the LLM's root_cause text via
-- the same keyword classifier pattern_detection_agent.py already uses,
-- but human-correctable, since keyword matching is deliberately simple
-- and won't always get it right.

ALTER TABLE exceptions
    ADD COLUMN IF NOT EXISTS root_cause_category TEXT,       -- one of ROOT_CAUSE_CATEGORIES, or NULL if unclassified
    ADD COLUMN IF NOT EXISTS root_cause_category_source TEXT; -- 'auto' | 'human' | NULL
