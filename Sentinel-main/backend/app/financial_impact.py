"""
Financial Impact Estimation -- calculation logic
---------------------------------------------------
Problem this solves: severity ("High") and SLA status ("Breached") tell
you an exception is bad, but not HOW bad in terms procurement actually
budgets against -- dollars. This turns order value + severity + SLA
status into a single estimated-dollars-at-risk figure per exception, so
exceptions can be prioritized and reported on the same way a finance
team already thinks about risk.

Deliberately rule-based and fully deterministic -- same philosophy as
monitoring_agent.py's severity scoring and sla.py's breach clock: a
number that drives prioritization and shows up in an executive report
needs to be explainable in one sentence and reproducible from the same
inputs, not a black box. The LLM (Ollama, wired in via
agents/financial_impact_agent.py) only ever generates the plain-English
explanation alongside this number -- it never influences the number
itself.
"""

# Expected-loss-style exposure percentage per severity -- NOT "this
# fraction of the order is definitely lost", but a rough proxy for
# things like expedited shipping premiums, spoilage/holding costs, or
# contract penalty exposure that scale with how bad the exception is.
# Tune these if your real contracts have known penalty clauses.
SEVERITY_IMPACT_PCT = {
    "Low": 0.05,
    "Medium": 0.15,
    "High": 0.35,
}
DEFAULT_SEVERITY_PCT = 0.15  # fallback if severity is somehow unrecognized

# Extra exposure once an exception has already blown through its SLA
# window (see app/sla.py) -- an unresolved High severity issue at hour 6
# is a bigger financial risk than the same issue at hour 1, so a breach
# adds a flat percentage-point bump on top of the severity component.
SLA_BREACH_ADD_ON_PCT = 0.10


def compute_order_value(quantity: int, unit_cost) -> float | None:
    """Returns quantity * unit_cost, or None if either input is missing --
    callers should treat None as "can't estimate, not $0 at risk"."""
    if quantity is None or unit_cost is None:
        return None
    return round(float(quantity) * float(unit_cost), 2)


def compute_financial_impact(order_value: float, severity: str, sla_breached: bool) -> dict:
    """
    Returns a breakdown dict (always -- never just a bare number) so the
    UI and audit log can show exactly how the figure was derived, not
    just the final dollar amount.
    """
    severity_pct = SEVERITY_IMPACT_PCT.get(severity, DEFAULT_SEVERITY_PCT)
    sla_addon_pct = SLA_BREACH_ADD_ON_PCT if sla_breached else 0.0
    total_pct = severity_pct + sla_addon_pct
    estimated_impact = round(order_value * total_pct, 2)

    return {
        "orderValue": order_value,
        "severity": severity,
        "severityPct": severity_pct,
        "slaBreached": sla_breached,
        "slaBreachAddOnPct": sla_addon_pct,
        "totalPct": round(total_pct, 4),
        "estimatedImpact": estimated_impact,
    }
