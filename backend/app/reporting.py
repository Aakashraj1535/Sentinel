"""
Scheduled Executive Reporting -- report formatting
----------------------------------------------------
Problem this solves: leadership and stakeholders who aren't in the tool
daily have no passive visibility into supply chain health -- they'd have
to remember to log in and check. This gives them a periodic digest
instead, delivered to channels they already check (email, Slack).

Kept separate from the DB-touching scheduling code (report_scheduler.py)
for the same reason as sla.py vs sla_monitor.py: pure formatting logic is
cheap and fast to unit test without a database, and that's exactly the
kind of thing worth locking down since a broken report template would
otherwise only be noticed when a real executive gets a garbled email.
"""

from datetime import datetime, timezone


def build_report_subject(now: datetime = None) -> str:
    now = now or datetime.now(timezone.utc)
    return f"[Sentinel] Weekly Supply Chain Digest — {now.strftime('%b %d, %Y')}"


def build_report_text(
    dashboard: dict,
    at_risk_suppliers: list,
    calibration: dict,
    now: datetime = None,
) -> str:
    """
    dashboard: the dict returned by serializers.dashboard_summary()
    at_risk_suppliers: list of supplier dicts (from serialize_supplier),
        pre-filtered/sorted by the caller to whichever are worth
        highlighting (e.g. riskLevel == 'High', already sorted worst-first)
    calibration: the dict returned by analytics.calibration_metrics()
    """
    now = now or datetime.now(timezone.utc)
    lines = []

    lines.append(f"SUPPLY CHAIN SENTINEL — WEEKLY DIGEST")
    lines.append(f"{now.strftime('%B %d, %Y')}")
    lines.append("")
    lines.append("EXCEPTION OVERVIEW")
    lines.append(f"  Active exceptions:      {dashboard.get('activeCount', 0)}")
    lines.append(f"  Resolved:               {dashboard.get('resolvedToday', 0)}")
    lines.append(f"  Escalations pending:    {dashboard.get('escalationsPending', 0)}")
    lines.append(f"  SLA breached:           {dashboard.get('slaBreachedCount', 0)}")
    lines.append(f"  SLA at risk:            {dashboard.get('slaAtRiskCount', 0)}")
    lines.append(f"  Avg. AI confidence:     {dashboard.get('avgConfidence', 0)}%")
    lines.append("")

    lines.append("SUPPLIERS NEEDING ATTENTION")
    if at_risk_suppliers:
        for s in at_risk_suppliers:
            lines.append(
                f"  - {s['name']} ({s['region']}): "
                f"{s['onTimeRate']}% on-time, {s['totalIncidents']} incidents "
                f"-- {s['riskLevel']} risk"
            )
    else:
        lines.append("  No suppliers currently at High risk. Nice week.")
    lines.append("")

    lines.append("AI RECOMMENDATION CALIBRATION")
    sample_size = calibration.get("totalDecided", 0)
    if sample_size > 0:
        lines.append(
            f"  Agreement rate: {calibration.get('agreementRate', 0)}% "
            f"(based on {sample_size} human decisions)"
        )
        if sample_size < 10:
            lines.append(
                "  Note: small sample size -- treat this figure as directional, "
                "not conclusive, until more decisions accumulate."
            )
    else:
        lines.append("  No human decisions recorded yet this period.")
    lines.append("")

    lines.append("(Sent automatically by Supply Chain Sentinel. "
                  "Log in to the dashboard for full detail.)")

    return "\n".join(lines)


def build_report_slack_text(
    dashboard: dict,
    at_risk_suppliers: list,
    now: datetime = None,
) -> str:
    """A shorter, Slack-friendly version -- full detail belongs in email/
    the dashboard, Slack is for a quick pulse-check, not a wall of text."""
    now = now or datetime.now(timezone.utc)
    top_risk_names = ", ".join(s["name"] for s in at_risk_suppliers[:3]) or "none"

    return (
        f":bar_chart: *Weekly Supply Chain Digest — {now.strftime('%b %d, %Y')}*\n"
        f"Active: {dashboard.get('activeCount', 0)} | "
        f"SLA Breached: {dashboard.get('slaBreachedCount', 0)} | "
        f"SLA At Risk: {dashboard.get('slaAtRiskCount', 0)} | "
        f"Avg. confidence: {dashboard.get('avgConfidence', 0)}%\n"
        f"Suppliers needing attention: {top_risk_names}"
    )
