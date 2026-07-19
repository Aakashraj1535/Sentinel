-- Migration 003: Predictive Risk Agent results cache
-- Run:  psql -p 5433 scs_db -f db/migration_003_predictive_risk.sql

CREATE TABLE IF NOT EXISTS predictive_risk (
    supplier_id             TEXT PRIMARY KEY REFERENCES suppliers(id),
    recent_incident_count   INTEGER NOT NULL DEFAULT 0,
    prior_incident_count    INTEGER NOT NULL DEFAULT 0,
    trend                   TEXT NOT NULL,          -- 'Rising' | 'Stable' | 'Improving'
    predicted_risk_level    TEXT NOT NULL,           -- 'Low' | 'Medium' | 'High'
    explanation             TEXT,
    computed_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);
