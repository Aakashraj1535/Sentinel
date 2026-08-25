"""
Serializers — convert database rows (snake_case) into the exact camelCase
JSON shapes defined in the frontend's mock-api.ts, so swapping from mock
data to real API calls requires zero changes on the frontend side.
"""

from app.db import get_dict_cursor
from app.sla import compute_sla_status, compute_sla_deadline, hours_remaining


def _iso(dt):
    return dt.isoformat() if dt else None


def serialize_exception(cur, exception_id: str) -> dict:
    cur.execute("""
        SELECT e.*, s.name AS supplier_name
        FROM exceptions e
        JOIN suppliers s ON s.id = e.supplier_id
        WHERE e.id = %s
    """, (exception_id,))
    exc = cur.fetchone()
    if not exc:
        return None

    cur.execute("""
        SELECT id, doc_label, doc_kind, excerpt
        FROM exception_knowledge WHERE exception_id = %s ORDER BY id
    """, (exception_id,))
    knowledge = [{
        "id": str(k["id"]),
        "label": k["doc_label"],
        "kind": k["doc_kind"],
        "excerpt": k["excerpt"],
    } for k in cur.fetchall()]

    cur.execute("""
        SELECT id, rank, action, estimated_cost, estimated_delivery,
               customer_impact, confidence_pct, confidence_level
        FROM recommendations WHERE exception_id = %s ORDER BY rank
    """, (exception_id,))
    recommendations = [{
        "id": str(r["id"]),
        "rank": r["rank"],
        "action": r["action"],
        "estimatedCost": r["estimated_cost"],
        "estimatedDelivery": r["estimated_delivery"],
        "customerImpact": r["customer_impact"],
        "confidencePct": float(r["confidence_pct"]) if r["confidence_pct"] is not None else 0,
        "confidence": r["confidence_level"],
    } for r in cur.fetchall()]

    cur.execute("""
        SELECT step, timestamp, summary FROM audit_log
        WHERE exception_id = %s ORDER BY id
    """, (exception_id,))
    audit = [{
        "step": a["step"],
        "timestamp": _iso(a["timestamp"]),
        "summary": a["summary"],
    } for a in cur.fetchall()]

    sla_status = compute_sla_status(exc["detected_at"], exc["severity"], exc["status"])
    sla_deadline = compute_sla_deadline(exc["detected_at"], exc["severity"])
    sla_hours_remaining = hours_remaining(exc["detected_at"], exc["severity"])

    return {
        "id": exc["id"],
        "supplier": exc["supplier_name"],
        "supplierId": exc["supplier_id"],
        "type": exc["exception_type"],
        "severity": exc["severity"],
        "status": exc["status"],
        "detectedAt": _iso(exc["detected_at"]),
        "rootCause": exc["root_cause"] or "",
        "rootCauseCategory": exc.get("root_cause_category"),
        "rootCauseCategorySource": exc.get("root_cause_category_source"),
        "autoResolved": exc["auto_resolved"],
        "escalationReason": exc["escalation_reason"],
        "humanDecision": exc.get("human_decision"),
        "humanDecisionNote": exc.get("human_decision_note"),
        "humanDecidedAt": _iso(exc.get("human_decided_at")),
        "humanDecidedBy": exc.get("human_decided_by"),
        "slaStatus": sla_status,
        "slaDeadline": _iso(sla_deadline),
        "slaHoursRemaining": sla_hours_remaining,
        "estimatedFinancialImpact": float(exc["estimated_financial_impact"]) if exc.get("estimated_financial_impact") is not None else None,
        "financialImpactBreakdown": exc.get("financial_impact_breakdown"),
        "financialImpactExplanation": exc.get("financial_impact_explanation"),
        "financialImpactComputedAt": _iso(exc.get("financial_impact_computed_at")),
        "knowledge": knowledge,
        "recommendations": recommendations,
        "audit": audit,
    }


def list_exceptions(cur, status: str = None) -> list:
    query = "SELECT id FROM exceptions"
    params = ()
    if status:
        query += " WHERE status = %s"
        params = (status,)
    query += " ORDER BY detected_at DESC"
    cur.execute(query, params)
    ids = [row["id"] for row in cur.fetchall()]
    return [serialize_exception(cur, eid) for eid in ids]


def serialize_supplier(cur, supplier_id: str) -> dict:
    from app.analytics import compute_risk_level

    cur.execute("SELECT * FROM suppliers WHERE id = %s", (supplier_id,))
    s = cur.fetchone()
    if not s:
        return None

    cur.execute("""
        SELECT id, exception_type, detected_at, severity
        FROM exceptions WHERE supplier_id = %s
        ORDER BY detected_at DESC LIMIT 5
    """, (supplier_id,))
    recent = [{
        "id": r["id"],
        "type": r["exception_type"],
        "date": _iso(r["detected_at"])[:10] if r["detected_at"] else None,
        "severity": r["severity"],
    } for r in cur.fetchall()]

    return {
        "id": s["id"],
        "name": s["name"],
        "region": s["region"],
        "onTimeRate": float(s["on_time_rate"]),
        "totalIncidents": s["total_incidents"],
        "riskLevel": compute_risk_level(float(s["on_time_rate"]), s["total_incidents"]),
        "recentIncidents": recent,
    }


def list_suppliers(cur) -> list:
    cur.execute("SELECT id FROM suppliers ORDER BY name")
    ids = [row["id"] for row in cur.fetchall()]
    return [serialize_supplier(cur, sid) for sid in ids]


def dashboard_summary(cur) -> dict:
    cur.execute("SELECT status, severity, detected_at FROM exceptions")
    rows = cur.fetchall()
    active_count = sum(1 for r in rows if r["status"] == "Active")
    resolved_count = sum(1 for r in rows if r["status"] == "Resolved")
    escalated_count = sum(1 for r in rows if r["status"] == "Escalated")

    sla_statuses = [
        compute_sla_status(r["detected_at"], r["severity"], r["status"]) for r in rows
    ]
    sla_breached_count = sum(1 for s in sla_statuses if s == "Breached")
    sla_at_risk_count = sum(1 for s in sla_statuses if s == "At Risk")

    cur.execute("SELECT confidence_pct FROM recommendations WHERE confidence_pct IS NOT NULL")
    confidences = [float(r["confidence_pct"]) for r in cur.fetchall()]
    avg_confidence = round(sum(confidences) / len(confidences)) if confidences else 0

    # Only sum impact for exceptions still open (Active/Escalated) -- a
    # Resolved exception's dollar exposure already played out, so it
    # shouldn't count toward "what's currently at risk" on the dashboard.
    cur.execute("""
        SELECT COALESCE(SUM(estimated_financial_impact), 0) as total
        FROM exceptions WHERE status IN ('Active', 'Escalated')
    """)
    total_at_risk = float(cur.fetchone()["total"])

    return {
        "activeCount": active_count,
        "resolvedToday": resolved_count,
        "slaBreachedCount": sla_breached_count,
        "slaAtRiskCount": sla_at_risk_count,
        "avgConfidence": avg_confidence,
        "escalationsPending": escalated_count,
        "totalFinancialImpactAtRisk": total_at_risk,
    }
