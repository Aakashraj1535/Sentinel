-- Migration 007: Financial Impact Ground Truth (research/evaluation only)
-- Run:  psql -p 5433 scs_db -f db/migration_007_ground_truth.sql
--
-- This table holds SYNTHETIC ground-truth dollar-loss values used only to
-- evaluate the Financial Impact agent's accuracy -- it is never read by
-- any agent or exposed via the API. Keeping it in a separate table (not
-- a column on `exceptions`) is deliberate: it guarantees the estimation
-- code path has zero access to it, so the evaluation is a genuine
-- held-out comparison rather than the model grading its own homework.
--
-- See backend/eval/generate_ground_truth.py for exactly how these values
-- are generated (documented there for the paper's methodology section).

CREATE TABLE IF NOT EXISTS financial_impact_ground_truth (
    exception_id    TEXT PRIMARY KEY REFERENCES exceptions(id),
    true_impact     NUMERIC(12,2) NOT NULL,
    true_breakdown  JSONB NOT NULL,       -- generative parameters used, for auditability
    generated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
