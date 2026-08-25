"""
Financial Impact Agent
------------------------
Hybrid design: the dollar figure itself comes from a deterministic
formula (app/financial_impact.py -- order value x severity x SLA-breach
status), and the local LLM (Ollama) only generates a short plain-English
explanation to sit alongside it. This keeps the number reproducible and
auditable while still giving a human-readable "why" for the dashboard,
same split used for grounding score (deterministic) vs resolution
options (LLM) in resolution_agent.py.

Requires Ollama running locally, e.g.:
    ollama pull llama3.2

Run standalone for testing:  python -m app.agents.financial_impact_agent
"""

import requests

from app.db import get_connection, get_dict_cursor
from app.sla import compute_sla_status
from app.financial_impact import compute_order_value, compute_financial_impact

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2"


def _generate_explanation(exception: dict, supplier_name: str, breakdown: dict) -> str:
    prompt = f"""Write ONE short sentence (max 30 words) explaining the estimated financial \
exposure of a supply chain exception for a procurement dashboard. Be factual, no headers, \
use the rupee symbol (Rs.) before amounts, not a dollar sign.

Exception type: {exception['exception_type']}
Severity: {exception['severity']}
Supplier: {supplier_name}
Order value: Rs. {breakdown['orderValue']:,.2f}
SLA breached: {"Yes" if breakdown['slaBreached'] else "No"}
Estimated impact: Rs. {breakdown['estimatedImpact']:,.2f} ({breakdown['totalPct'] * 100:.0f}% of order value)
"""
    try:
        response = requests.post(OLLAMA_URL, json={
            "model": OLLAMA_MODEL, "prompt": prompt, "stream": False,
        }, timeout=60)
        response.raise_for_status()
        return response.json()["response"].strip()
    except Exception:
        breach_note = " and it has already breached its SLA window" if breakdown["slaBreached"] else ""
        return (
            f"Estimated Rs. {breakdown['estimatedImpact']:,.2f} at risk on a "
            f"Rs. {breakdown['orderValue']:,.2f} order from {supplier_name}, based on "
            f"{exception['severity']} severity{breach_note}."
        )


def estimate_financial_impact(exception_id: str) -> dict:
    """
    Computes and persists the financial impact estimate for one
    exception. Safe to re-run -- always recomputes from current data
    (order value doesn't change, but SLA-breach status can, so a
    re-run after a breach will correctly bump the estimate up).
    """
    conn = get_connection()
    cur = get_dict_cursor(conn)

    cur.execute("SELECT * FROM exceptions WHERE id = %s", (exception_id,))
    exception = cur.fetchone()
    if not exception:
        cur.close()
        conn.close()
        raise ValueError(f"Exception {exception_id} not found")

    cur.execute("SELECT name FROM suppliers WHERE id = %s", (exception["supplier_id"],))
    supplier = cur.fetchone()
    supplier_name = supplier["name"] if supplier else exception["supplier_id"]

    order = None
    if exception["order_id"]:
        cur.execute("SELECT quantity, unit_cost FROM orders WHERE id = %s", (exception["order_id"],))
        order = cur.fetchone()

    order_value = compute_order_value(order["quantity"], order["unit_cost"]) if order else None

    if order_value is None:
        # No order linked, or unit_cost hasn't been backfilled yet -- log
        # why rather than silently writing nothing, so it's obvious from
        # the audit trail that this isn't a $0-impact exception, it's an
        # unpriced one.
        reason = (
            "No linked order found." if not order
            else "Order has no unit_cost recorded (run db/backfill_unit_cost.py)."
        )
        cur.execute("""
            UPDATE exceptions
            SET estimated_financial_impact = NULL,
                financial_impact_breakdown = NULL,
                financial_impact_explanation = %s,
                financial_impact_computed_at = now()
            WHERE id = %s
        """, (f"Could not estimate financial impact: {reason}", exception_id))
        cur.execute("""
            INSERT INTO audit_log (exception_id, step, summary)
            VALUES (%s, 'Financial Impact Skipped', %s)
        """, (exception_id, reason))
        conn.commit()
        cur.close()
        conn.close()
        return {
            "exception_id": exception_id,
            "estimated_impact": None,
            "breakdown": None,
            "explanation": reason,
        }

    sla_breached = compute_sla_status(
        exception["detected_at"], exception["severity"], exception["status"]
    ) == "Breached"

    breakdown = compute_financial_impact(order_value, exception["severity"], sla_breached)
    explanation = _generate_explanation(exception, supplier_name, breakdown)

    import json
    cur.execute("""
        UPDATE exceptions
        SET estimated_financial_impact = %s,
            financial_impact_breakdown = %s,
            financial_impact_explanation = %s,
            financial_impact_computed_at = now()
        WHERE id = %s
    """, (breakdown["estimatedImpact"], json.dumps(breakdown), explanation, exception_id))

    cur.execute("""
        INSERT INTO audit_log (exception_id, step, summary)
        VALUES (%s, 'Financial Impact Estimated', %s)
    """, (exception_id,
          f"Estimated Rs. {breakdown['estimatedImpact']:,.2f} at risk "
          f"({breakdown['totalPct'] * 100:.0f}% of Rs. {breakdown['orderValue']:,.2f} order value)."))

    conn.commit()
    cur.close()
    conn.close()

    return {
        "exception_id": exception_id,
        "estimated_impact": breakdown["estimatedImpact"],
        "breakdown": breakdown,
        "explanation": explanation,
    }


if __name__ == "__main__":
    conn = get_connection()
    cur = get_dict_cursor(conn)
    cur.execute("SELECT id FROM exceptions ORDER BY detected_at DESC LIMIT 1")
    sample = cur.fetchone()
    cur.close()
    conn.close()

    if not sample:
        print("No exceptions found — run the monitoring agent first.")
    else:
        exc_id = sample["id"]
        print(f"Estimating financial impact for {exc_id}...\n")
        result = estimate_financial_impact(exc_id)
        if result["estimated_impact"] is not None:
            print(f"Estimated impact: Rs. {result['estimated_impact']:,.2f}")
            print(f"Breakdown: {result['breakdown']}")
        print(f"\nExplanation: {result['explanation']}")
