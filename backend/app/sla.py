"""
SLA Timers & Auto-Escalation
-----------------------------
Deliberately rule-based, not LLM-based — this is a clock, not a judgment
call, so it should be 100% deterministic and explainable, same philosophy
as monitoring_agent.py's severity scoring.

The problem this solves: an exception can currently sit at 'Active'
(waiting for the AI pipeline to process it) or 'Escalated' (waiting for a
human to approve/reject) indefinitely if nobody happens to check the
dashboard. There's no clock forcing a response. This module is that clock.

SLA windows are per-severity, reflecting that a High severity exception
deserves a faster response than a Low one. The SLA is considered "done"
(no longer tracked) once status == 'Resolved' -- an Escalated exception
that was Rejected by a human is still open and still SLA-tracked, since
rejecting a recommendation doesn't mean the underlying problem went away.
"""

from datetime import datetime, timedelta, timezone

# Hours allowed from detection until a human (or the AI, for Active items
# still in the pipeline) needs to have acted, per severity. These mirror
# real procurement SLA conventions: high severity gets hours, not days.
SLA_HOURS_BY_SEVERITY = {
    "High": 4,
    "Medium": 24,
    "Low": 72,
}

# An exception counts as "At Risk" once it has used up this fraction of
# its total SLA window, giving an early warning before it actually
# breaches -- e.g. a High severity exception (4h window) flips to
# At Risk at the 3-hour mark (75%), not just at the 4-hour breach point.
AT_RISK_THRESHOLD_FRACTION = 0.75

# Statuses considered "SLA complete" -- the clock stops here.
SLA_TERMINAL_STATUSES = {"Resolved"}


def sla_hours_for_severity(severity: str) -> int:
    """Falls back to the most generous (Low) window for an unrecognized
    severity value, rather than crashing or silently using 0."""
    return SLA_HOURS_BY_SEVERITY.get(severity, SLA_HOURS_BY_SEVERITY["Low"])


def compute_sla_deadline(detected_at: datetime, severity: str) -> datetime:
    """The absolute point in time this exception's SLA is breached."""
    return detected_at + timedelta(hours=sla_hours_for_severity(severity))


def compute_sla_status(
    detected_at: datetime,
    severity: str,
    status: str,
    now: datetime = None,
) -> str:
    """
    Returns one of: 'Complete', 'On Track', 'At Risk', 'Breached'.

    'Complete' means the exception reached a terminal status and the SLA
    clock has stopped (regardless of whether it was breached along the
    way -- we don't retroactively flag something as breached once it's
    actually done, since what matters going forward is what still needs
    attention).
    """
    if status in SLA_TERMINAL_STATUSES:
        return "Complete"

    now = now or datetime.now(timezone.utc)
    hours = sla_hours_for_severity(severity)
    deadline = compute_sla_deadline(detected_at, severity)
    at_risk_point = detected_at + timedelta(hours=hours * AT_RISK_THRESHOLD_FRACTION)

    if now >= deadline:
        return "Breached"
    if now >= at_risk_point:
        return "At Risk"
    return "On Track"


def hours_remaining(detected_at: datetime, severity: str, now: datetime = None) -> float:
    """Negative once breached (how many hours overdue)."""
    now = now or datetime.now(timezone.utc)
    deadline = compute_sla_deadline(detected_at, severity)
    return round((deadline - now).total_seconds() / 3600, 1)
