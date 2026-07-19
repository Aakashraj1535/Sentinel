"""
Report Agent
-------------
Compiles everything the pipeline has produced for an exception — detection
details, retrieved knowledge, ranked recommendations, and the audit trail —
into one structured incident report. Uses the local LLM for a short,
readable narrative summary (2-3 sentences), while all factual details
(dates, scores, actions) come directly from the database, not the LLM,
so numbers can't be hallucinated.

Run standalone for testing:  python -m app.agents.report_agent
"""

import requests

from app.db import get_connection, get_dict_cursor

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2"


def _summarize_with_llm(exception: dict, top_recommendation: dict) -> str:
    prompt = f"""Write a short, plain-English summary (2-3 sentences max) of this \
supply chain incident for a business report. Be factual and concise, no headers or bullet points.

Exception type: {exception['exception_type']}
Severity: {exception['severity']}
Root cause: {exception['root_cause']}
Status: {exception['status']}
Top recommendation: {top_recommendation['action'] if top_recommendation else 'None'}
"""
    try:
        response = requests.post(OLLAMA_URL, json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
        }, timeout=60)
        response.raise_for_status()
        return response.json()["response"].strip()
    except Exception:
        # Fallback to a templated summary if Ollama is unavailable —
        # the report should still work even if the LLM call fails.
        return (
            f"A {exception['severity'].lower()}-severity {exception['exception_type'].lower()} "
            f"was detected and is currently {exception['status'].lower()}. "
            f"Root cause: {exception['root_cause'] or 'not determined'}."
        )


def generate_report(exception_id: str) -> dict:
    conn = get_connection()
    cur = get_dict_cursor(conn)

    cur.execute("""
        SELECT e.*, s.name AS supplier_name, s.on_time_rate, o.item, o.quantity
        FROM exceptions e
        JOIN suppliers s ON s.id = e.supplier_id
        LEFT JOIN orders o ON o.id = e.order_id
        WHERE e.id = %s
    """, (exception_id,))
    exception = cur.fetchone()
    if not exception:
        cur.close()
        conn.close()
        raise ValueError(f"Exception {exception_id} not found")

    cur.execute("""
        SELECT rank, action, estimated_cost, estimated_delivery,
               customer_impact, confidence_pct, confidence_level
        FROM recommendations
        WHERE exception_id = %s ORDER BY rank
    """, (exception_id,))
    recommendations = cur.fetchall()

    cur.execute("""
        SELECT step, timestamp, summary FROM audit_log
        WHERE exception_id = %s ORDER BY id
    """, (exception_id,))
    audit_trail = cur.fetchall()

    top_rec = recommendations[0] if recommendations else None
    narrative_summary = _summarize_with_llm(exception, top_rec)

    cur.execute("""
        INSERT INTO audit_log (exception_id, step, summary)
        VALUES (%s, 'Reported', %s)
    """, (exception_id, "Incident report generated."))
    conn.commit()
    cur.close()
    conn.close()

    return {
        "exception_id": exception_id,
        "exception_type": exception["exception_type"],
        "severity": exception["severity"],
        "status": exception["status"],
        "supplier_name": exception["supplier_name"],
        "item": exception["item"],
        "quantity": exception["quantity"],
        "root_cause": exception["root_cause"],
        "narrative_summary": narrative_summary,
        "auto_resolved": exception["auto_resolved"],
        "escalation_reason": exception["escalation_reason"],
        "recommendations": [dict(r) for r in recommendations],
        "audit_trail": [dict(a) for a in audit_trail],
    }


def format_report_markdown(report: dict) -> str:
    """Renders the report dict as readable markdown, e.g. for a dashboard view or export."""
    lines = [
        f"# Incident Report — {report['exception_id']}",
        "",
        f"**Type:** {report['exception_type']}  ",
        f"**Severity:** {report['severity']}  ",
        f"**Status:** {report['status']}  ",
        f"**Supplier:** {report['supplier_name']}  ",
        f"**Item:** {report['item']} (qty: {report['quantity']})  ",
        "",
        "## Summary",
        report["narrative_summary"],
        "",
        "## Root Cause",
        report["root_cause"] or "Not determined.",
        "",
        "## Recommended Actions",
    ]
    for r in report["recommendations"]:
        lines.append(
            f"{r['rank']}. **{r['action']}** — Cost: {r['estimated_cost']}, "
            f"Time: {r['estimated_delivery']}, Impact: {r['customer_impact']}, "
            f"Confidence: {r['confidence_pct']}% ({r['confidence_level']})"
        )
    if report["escalation_reason"]:
        lines += ["", f"⚠️ **Escalated:** {report['escalation_reason']}"]
    lines += ["", "## Audit Trail"]
    for a in report["audit_trail"]:
        lines.append(f"- `{a['timestamp']}` **{a['step']}** — {a['summary']}")
    return "\n".join(lines)


if __name__ == "__main__":
    conn = get_connection()
    cur = get_dict_cursor(conn)
    cur.execute("""
        SELECT id FROM exceptions
        WHERE status IN ('Resolved', 'Escalated') ORDER BY id LIMIT 1
    """)
    sample = cur.fetchone()
    cur.close()
    conn.close()

    if not sample:
        print("No resolved/escalated exceptions found — run the resolution agent first.")
    else:
        report = generate_report(sample["id"])
        print(format_report_markdown(report))
