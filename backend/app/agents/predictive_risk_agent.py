"""
Predictive Risk Agent
-----------------------
Every other agent in this system is REACTIVE — it responds to an exception
that has already happened. This agent is PROACTIVE: it looks at each
supplier's recent incident trend (not just their overall historical rate)
and flags suppliers who are trending toward becoming a problem, before a
new exception is even detected.

Trend detection is deliberately simple and explainable (not a trained
model) — it compares incident counts in two adjacent time windows. This
keeps it consistent with the rest of the system's "simple, transparent
formulas over black-box ML" design philosophy.

Run standalone for testing:  python -m app.agents.predictive_risk_agent
"""

import requests
from datetime import datetime, timedelta, timezone

from app.db import get_connection, get_dict_cursor
from app.analytics import compute_risk_level

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2"

RECENT_WINDOW_DAYS = 14
PRIOR_WINDOW_DAYS = 14


def compute_trend(cur, supplier_id: str) -> dict:
    now = datetime.now(timezone.utc)
    recent_start = now - timedelta(days=RECENT_WINDOW_DAYS)
    prior_start = now - timedelta(days=RECENT_WINDOW_DAYS + PRIOR_WINDOW_DAYS)

    cur.execute("""
        SELECT count(*) as c FROM exceptions
        WHERE supplier_id = %s AND detected_at >= %s
    """, (supplier_id, recent_start))
    recent_count = cur.fetchone()["c"]

    cur.execute("""
        SELECT count(*) as c FROM exceptions
        WHERE supplier_id = %s AND detected_at >= %s AND detected_at < %s
    """, (supplier_id, prior_start, recent_start))
    prior_count = cur.fetchone()["c"]

    # Simple, explainable trend rule — not a trained model.
    if recent_count >= 2 and recent_count > prior_count * 1.5:
        trend = "Rising"
    elif prior_count > 0 and recent_count < prior_count * 0.5:
        trend = "Improving"
    else:
        trend = "Stable"

    return {
        "recent_count": recent_count,
        "prior_count": prior_count,
        "trend": trend,
    }


def predicted_level(current_risk_level: str, trend: str) -> str:
    """Adjusts the supplier's current risk tier based on its trend direction."""
    tiers = ["Low", "Medium", "High"]
    idx = tiers.index(current_risk_level)

    if trend == "Rising":
        idx = min(idx + 1, len(tiers) - 1)
    elif trend == "Improving":
        idx = max(idx - 1, 0)
    return tiers[idx]


def _generate_explanation(supplier_name: str, trend_info: dict, recent_incident_texts: list) -> str:
    if trend_info["trend"] == "Stable" and not recent_incident_texts:
        return f"No significant change in {supplier_name}'s incident pattern."

    context = "\n".join(f"- {t}" for t in recent_incident_texts) or "No recent incident details available."
    prompt = f"""Write ONE short sentence (max 25 words) summarizing this supplier's risk trend \
for a procurement dashboard. Be factual, no headers.

Supplier: {supplier_name}
Trend: {trend_info['trend']}
Recent incidents (last {RECENT_WINDOW_DAYS} days): {trend_info['recent_count']}
Prior period incidents: {trend_info['prior_count']}
Recent incident details:
{context}
"""
    try:
        response = requests.post(OLLAMA_URL, json={
            "model": OLLAMA_MODEL, "prompt": prompt, "stream": False,
        }, timeout=60)
        response.raise_for_status()
        return response.json()["response"].strip()
    except Exception:
        return (f"{supplier_name} shows a {trend_info['trend'].lower()} trend "
                f"({trend_info['recent_count']} incidents in the last {RECENT_WINDOW_DAYS} days "
                f"vs {trend_info['prior_count']} in the prior period).")


def run_predictive_risk_analysis() -> list:
    """
    Recomputes trend + predicted risk for every supplier and stores results.
    Returns the list of results, sorted highest predicted risk first.
    """
    conn = get_connection()
    cur = get_dict_cursor(conn)

    cur.execute("SELECT id, name, on_time_rate, total_incidents FROM suppliers")
    suppliers = cur.fetchall()

    results = []
    for s in suppliers:
        trend_info = compute_trend(cur, s["id"])
        current_level = compute_risk_level(float(s["on_time_rate"]), s["total_incidents"])
        forecast_level = predicted_level(current_level, trend_info["trend"])

        cur.execute("""
            SELECT chunk_text FROM knowledge_documents
            WHERE supplier_id = %s AND doc_kind = 'Incident'
            ORDER BY id DESC LIMIT 3
        """, (s["id"],))
        recent_texts = [r["chunk_text"] for r in cur.fetchall()]

        explanation = _generate_explanation(s["name"], trend_info, recent_texts)

        cur.execute("""
            INSERT INTO predictive_risk
                (supplier_id, recent_incident_count, prior_incident_count,
                 trend, predicted_risk_level, explanation, computed_at)
            VALUES (%s, %s, %s, %s, %s, %s, now())
            ON CONFLICT (supplier_id) DO UPDATE SET
                recent_incident_count = EXCLUDED.recent_incident_count,
                prior_incident_count = EXCLUDED.prior_incident_count,
                trend = EXCLUDED.trend,
                predicted_risk_level = EXCLUDED.predicted_risk_level,
                explanation = EXCLUDED.explanation,
                computed_at = EXCLUDED.computed_at
        """, (s["id"], trend_info["recent_count"], trend_info["prior_count"],
              trend_info["trend"], forecast_level, explanation))

        results.append({
            "supplierId": s["id"],
            "supplierName": s["name"],
            "trend": trend_info["trend"],
            "recentIncidentCount": trend_info["recent_count"],
            "priorIncidentCount": trend_info["prior_count"],
            "currentRiskLevel": current_level,
            "predictedRiskLevel": forecast_level,
            "explanation": explanation,
        })

    conn.commit()
    cur.close()
    conn.close()

    risk_order = {"High": 0, "Medium": 1, "Low": 2}
    results.sort(key=lambda r: risk_order[r["predictedRiskLevel"]])
    return results


def get_cached_risk_forecast() -> list:
    """Fast read of the last computed forecast, for the API to serve without recomputing."""
    conn = get_connection()
    cur = get_dict_cursor(conn)
    cur.execute("""
        SELECT pr.*, s.name as supplier_name
        FROM predictive_risk pr
        JOIN suppliers s ON s.id = pr.supplier_id
        ORDER BY
            CASE pr.predicted_risk_level WHEN 'High' THEN 0 WHEN 'Medium' THEN 1 ELSE 2 END
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [{
        "supplierId": r["supplier_id"],
        "supplierName": r["supplier_name"],
        "trend": r["trend"],
        "recentIncidentCount": r["recent_incident_count"],
        "priorIncidentCount": r["prior_incident_count"],
        "predictedRiskLevel": r["predicted_risk_level"],
        "explanation": r["explanation"],
        "computedAt": r["computed_at"].isoformat() if r["computed_at"] else None,
    } for r in rows]


if __name__ == "__main__":
    print("Running predictive risk analysis for all suppliers...\n")
    results = run_predictive_risk_analysis()
    for r in results:
        print(f"{r['supplierName']} ({r['supplierId']}) — "
              f"Trend: {r['trend']}, Predicted Risk: {r['predictedRiskLevel']}")
        print(f"  {r['explanation']}")
        print()
