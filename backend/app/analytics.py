"""
Analytics — aggregated data for dashboard charts and supplier risk scoring.
All derived from existing tables; no new tables needed.
"""

from datetime import datetime, timedelta, timezone


def supplier_weekly_trend(cur, supplier_id: str, weeks: int = 12) -> dict:
    """
    Real historical on-time-rate trend for one supplier, computed
    directly from actual order delivery history (expected_delivery vs
    actual_delivery) -- NOT from suppliers.on_time_rate, which is a
    static seeded value nothing in this codebase ever updates, so it
    can't show movement over time even if you wanted it to.

    Returns weekly on-time rate + order count (for a trend chart), plus
    a trend_direction verdict comparing the most recent half of the
    window against the earlier half.
    """
    from app.supplier_trend import compute_trend_direction

    since = datetime.now(timezone.utc) - timedelta(weeks=weeks)
    cur.execute("""
        SELECT date_trunc('week', actual_delivery) as week,
               actual_delivery <= expected_delivery as was_on_time
        FROM orders
        WHERE supplier_id = %s AND actual_delivery IS NOT NULL
              AND actual_delivery >= %s
        ORDER BY week
    """, (supplier_id, since))
    rows = cur.fetchall()

    by_week = {}
    for r in rows:
        week_str = r["week"].date().isoformat()
        bucket = by_week.setdefault(week_str, {"total": 0, "onTime": 0})
        bucket["total"] += 1
        if r["was_on_time"]:
            bucket["onTime"] += 1

    weekly_series = [
        {
            "week": week,
            "onTimeRate": round((b["onTime"] / b["total"]) * 100, 1),
            "orderCount": b["total"],
            "onTimeCount": b["onTime"],
        }
        for week, b in sorted(by_week.items())
    ]

    # Split the window in half to compare "recently" vs "before that" --
    # simpler and more transparent than a rolling regression, and easy
    # to explain in a supplier conversation ("last 6 weeks vs the 6
    # before that").
    midpoint = len(weekly_series) // 2
    prior_weeks = weekly_series[:midpoint]
    recent_weeks = weekly_series[midpoint:]

    def _aggregate(series):
        total_orders = sum(w["orderCount"] for w in series)
        if total_orders == 0:
            return 0.0, 0
        total_on_time = sum(w["onTimeCount"] for w in series)
        return round((total_on_time / total_orders) * 100, 1), total_orders

    recent_rate, recent_count = _aggregate(recent_weeks)
    prior_rate, prior_count = _aggregate(prior_weeks)

    trend_direction = compute_trend_direction(recent_rate, recent_count, prior_rate, prior_count)

    return {
        "supplierId": supplier_id,
        "weeklySeries": weekly_series,
        "trendDirection": trend_direction,
        "recentOnTimeRate": recent_rate,
        "priorOnTimeRate": prior_rate,
    }


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


def root_cause_breakdown(cur, weeks: int = 12) -> dict:
    """
    Structured root-cause counts for trend analysis -- the point being
    to answer "what's our biggest recurring problem lately" without
    anyone reading every exception's free-text root_cause by hand.

    'Uncategorized' covers two real, distinct situations, both grouped
    together deliberately since from a leadership-dashboard view they
    mean the same thing -- "we don't have an answer here yet":
      - exceptions not yet resolved (no root_cause text at all)
      - exceptions resolved, but whose root_cause text didn't match any
        known keyword pattern and hasn't been human-tagged either
    """
    from app.root_cause import ROOT_CAUSE_CATEGORIES

    since = datetime.now(timezone.utc) - timedelta(weeks=weeks)

    # Overall breakdown (all-time, not just the trend window) -- this is
    # the "what's our biggest problem, period" answer.
    cur.execute("SELECT root_cause_category, count(*) as c FROM exceptions GROUP BY root_cause_category")
    overall_rows = cur.fetchall()
    overall = {cat: 0 for cat in ROOT_CAUSE_CATEGORIES}
    overall["Uncategorized"] = 0
    for r in overall_rows:
        cat = r["root_cause_category"]
        if cat in overall:
            overall[cat] = r["c"]
        else:
            overall["Uncategorized"] += r["c"]

    # Weekly trend -- this is the "is it getting better or worse"
    # answer, which a single overall count can't show.
    cur.execute("""
        SELECT date_trunc('week', detected_at) as week, root_cause_category, count(*) as c
        FROM exceptions
        WHERE detected_at >= %s
        GROUP BY week, root_cause_category
        ORDER BY week
    """, (since,))
    trend_rows = cur.fetchall()

    by_week = {}
    for r in trend_rows:
        week_str = r["week"].date().isoformat()
        by_week.setdefault(week_str, {"week": week_str})
        cat = r["root_cause_category"] if r["root_cause_category"] in ROOT_CAUSE_CATEGORIES else "Uncategorized"
        by_week[week_str][cat] = by_week[week_str].get(cat, 0) + r["c"]

    trend = sorted(by_week.values(), key=lambda x: x["week"])

    return {
        "overall": overall,
        "trend": trend,
        "categories": ROOT_CAUSE_CATEGORIES + ["Uncategorized"],
    }


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
