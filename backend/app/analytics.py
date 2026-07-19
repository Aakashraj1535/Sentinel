"""
Analytics — aggregated data for dashboard charts and supplier risk scoring.
All derived from existing tables; no new tables needed.
"""

from datetime import datetime, timedelta, timezone


def severity_distribution(cur) -> dict:
    cur.execute("SELECT severity, count(*) as c FROM exceptions GROUP BY severity")
    rows = {r["severity"]: r["c"] for r in cur.fetchall()}
    return {"Low": rows.get("Low", 0), "Medium": rows.get("Medium", 0), "High": rows.get("High", 0)}


def type_distribution(cur) -> list:
    cur.execute("SELECT exception_type, count(*) as c FROM exceptions GROUP BY exception_type ORDER BY c DESC")
    return [{"type": r["exception_type"], "count": r["c"]} for r in cur.fetchall()]


def resolution_trend(cur, days: int = 14) -> list:
    """Exceptions detected per day for the last N days, split by outcome."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    cur.execute("""
        SELECT date(detected_at) as day, status, count(*) as c
        FROM exceptions
        WHERE detected_at >= %s
        GROUP BY day, status
        ORDER BY day
    """, (since,))
    rows = cur.fetchall()

    by_day = {}
    for r in rows:
        day_str = r["day"].isoformat()
        by_day.setdefault(day_str, {"date": day_str, "resolved": 0, "escalated": 0, "active": 0})
        key = r["status"].lower()
        if key in by_day[day_str]:
            by_day[day_str][key] = r["c"]

    return sorted(by_day.values(), key=lambda x: x["date"])


def auto_resolved_rate(cur) -> dict:
    cur.execute("SELECT status, count(*) as c FROM exceptions GROUP BY status")
    rows = {r["status"]: r["c"] for r in cur.fetchall()}
    total = sum(rows.values())
    resolved = rows.get("Resolved", 0)
    rate = round((resolved / total) * 100, 1) if total else 0
    return {"autoResolvedRate": rate, "totalProcessed": total}


def calibration_metrics(cur) -> dict:
    """
    Tracks whether human Approve/Reject decisions agree with the AI's
    own confidence — a real, growing accuracy signal instead of a
    one-time offline test. 'Agreement' means a human approved a
    recommendation the AI was already confident about, or rejected one
    it was unsure about; disagreement is the interesting/informative case.
    """
    cur.execute("""
        SELECT e.id, e.human_decision,
               (SELECT confidence_pct FROM recommendations
                WHERE exception_id = e.id ORDER BY rank LIMIT 1) as top_confidence
        FROM exceptions e
        WHERE e.human_decision IS NOT NULL
    """)
    rows = cur.fetchall()

    total_decided = len(rows)
    approved = sum(1 for r in rows if r["human_decision"] == "Approved")
    rejected = sum(1 for r in rows if r["human_decision"] == "Rejected")

    approved_confidences = [float(r["top_confidence"]) for r in rows
                             if r["human_decision"] == "Approved" and r["top_confidence"] is not None]
    rejected_confidences = [float(r["top_confidence"]) for r in rows
                             if r["human_decision"] == "Rejected" and r["top_confidence"] is not None]

    agreement_rate = round((approved / total_decided) * 100, 1) if total_decided else None
    avg_confidence_approved = round(sum(approved_confidences) / len(approved_confidences), 1) if approved_confidences else None
    avg_confidence_rejected = round(sum(rejected_confidences) / len(rejected_confidences), 1) if rejected_confidences else None

    return {
        "totalDecided": total_decided,
        "approved": approved,
        "rejected": rejected,
        "agreementRate": agreement_rate,
        "avgConfidenceWhenApproved": avg_confidence_approved,
        "avgConfidenceWhenRejected": avg_confidence_rejected,
    }


def analytics_summary(cur) -> dict:
    return {
        "severityDistribution": severity_distribution(cur),
        "typeDistribution": type_distribution(cur),
        "resolutionTrend": resolution_trend(cur),
        **auto_resolved_rate(cur),
    }


def compute_risk_level(on_time_rate: float, total_incidents: int) -> str:
    """
    Simple weighted risk formula — deliberately transparent, not a trained model.
    Low on-time rate OR a high incident count independently push risk up.
    """
    if on_time_rate < 85 or total_incidents >= 6:
        return "High"
    elif on_time_rate < 93 or total_incidents >= 3:
        return "Medium"
    return "Low"


def notifications_feed(cur, limit: int = 20) -> list:
    """
    Simulated notification feed derived from exception outcomes —
    no separate notifications table; these are synthesized from
    existing exception + audit data to represent what would be sent
    to procurement/logistics/management in a real deployment.
    """
    cur.execute("""
        SELECT e.id, e.exception_type, e.severity, e.status, e.supplier_id,
               e.escalation_reason, e.detected_at, s.name as supplier_name
        FROM exceptions e
        JOIN suppliers s ON s.id = e.supplier_id
        WHERE e.status IN ('Resolved', 'Escalated')
        ORDER BY e.detected_at DESC
        LIMIT %s
    """, (limit,))
    rows = cur.fetchall()

    notifications = []
    for r in rows:
        if r["status"] == "Escalated":
            notifications.append({
                "id": f"NOTIF-{r['id']}",
                "type": "escalation",
                "audience": "Procurement",
                "message": f"{r['exception_type']} ({r['severity']} severity) for {r['supplier_name']} "
                           f"requires review: {r['escalation_reason']}",
                "exceptionId": r["id"],
                "timestamp": r["detected_at"].isoformat() if r["detected_at"] else None,
            })
        else:
            notifications.append({
                "id": f"NOTIF-{r['id']}",
                "type": "resolution",
                "audience": "Warehouse",
                "message": f"{r['exception_type']} for {r['supplier_name']} auto-resolved.",
                "exceptionId": r["id"],
                "timestamp": r["detected_at"].isoformat() if r["detected_at"] else None,
            })
    return notifications
