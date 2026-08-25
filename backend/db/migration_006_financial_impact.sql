-- Migration 006: Financial Impact Estimation
-- Run:  psql -p 5433 scs_db -f db/migration_006_financial_impact.sql
--
-- Adds a per-order cost basis (unit_cost -- didn't exist anywhere in the
-- schema before this) and, on exceptions, a rule-based dollar estimate of
-- what's at risk plus an LLM-generated one-sentence explanation of why.
--
-- The number itself (estimated_financial_impact) is always deterministic --
-- computed from order value x severity x SLA-breach status, see
-- app/financial_impact.py -- so it's reproducible and auditable. The LLM
-- (Ollama) only ever writes the explanation text, never the figure, same
-- separation of concerns as root_cause vs root_cause_category.

ALTER TABLE orders
    ADD COLUMN IF NOT EXISTS unit_cost NUMERIC(10,2);  -- NULL until backfilled; see db/backfill_unit_cost.py

ALTER TABLE exceptions
    ADD COLUMN IF NOT EXISTS estimated_financial_impact NUMERIC(12,2),  -- dollar amount at risk
    ADD COLUMN IF NOT EXISTS financial_impact_breakdown JSONB,          -- {orderValue, severityPct, slaBreachAddOnPct, ...}
    ADD COLUMN IF NOT EXISTS financial_impact_explanation TEXT,         -- LLM-generated one-liner, never drives the number
    ADD COLUMN IF NOT EXISTS financial_impact_computed_at TIMESTAMPTZ;
