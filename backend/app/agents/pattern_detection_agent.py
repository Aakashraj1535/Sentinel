"""
Cross-Supplier Pattern Detection
-----------------------------------
Different from the Predictive Risk Agent (which looks at ONE supplier's
trend over time), this looks ACROSS all suppliers at a point in time to
spot systemic patterns — e.g. multiple unrelated suppliers all citing
port congestion in the same week suggests a regional infrastructure
problem, not individual supplier failures.

Detection is a simple grouping/counting rule (not ML): if 2+ distinct
suppliers have incidents with similar root-cause keywords within the
same recent window, it's flagged as a potential systemic pattern.
"""

import re
import requests
from datetime import datetime, timedelta, timezone
from collections import defaultdict

from app.db import get_connection, get_dict_cursor

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2"

PATTERN_WINDOW_DAYS = 21

# Keyword groups used to cluster incidents by likely shared cause.
# Simple keyword matching — deliberately not ML, stays explainable.
CAUSE_KEYWORDS = {
    "Port / logistics congestion": ["port congestion", "highway closure", "flooding"],
    "Customs / documentation": ["customs", "documentation"],
    "Supplier capacity issues": ["production line", "raw material shortage", "capacity"],
    "Quality control": ["defect", "quality", "incorrect quantity"],
}


def _classify_cause(root_cause_text: str) -> str:
    if not root_cause_text:
        return None
    text = root_cause_text.lower()
    for label, keywords in CAUSE_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return label
    return None


def detect_systemic_patterns() -> list:
    conn = get_connection()
    cur = get_dict_cursor(conn)

    since = datetime.now(timezone.utc) - timedelta(days=PATTERN_WINDOW_DAYS)
    cur.execute("""
        SELECT e.id, e.supplier_id, e.root_cause, e.detected_at, s.name as supplier_name
        FROM exceptions e
        JOIN suppliers s ON s.id = e.supplier_id
        WHERE e.detected_at >= %s AND e.root_cause IS NOT NULL
    """, (since,))
    rows = cur.fetchall()

    # Group by classified cause; track which DISTINCT suppliers are affected
    groups = defaultdict(lambda: {"suppliers": set(), "exception_ids": [], "supplier_names": set()})
    for r in rows:
        cause = _classify_cause(r["root_cause"])
        if cause:
            groups[cause]["suppliers"].add(r["supplier_id"])
            groups[cause]["supplier_names"].add(r["supplier_name"])
            groups[cause]["exception_ids"].append(r["id"])

    patterns = []
    for cause_label, data in groups.items():
        if len(data["suppliers"]) >= 2:  # only flag if 2+ DISTINCT suppliers affected
            explanation = _generate_pattern_explanation(
                cause_label, list(data["supplier_names"]), len(data["exception_ids"])
            )
            patterns.append({
                "causeCategory": cause_label,
                "affectedSupplierCount": len(data["suppliers"]),
                "affectedSuppliers": list(data["supplier_names"]),
                "totalIncidents": len(data["exception_ids"]),
                "exceptionIds": data["exception_ids"],
                "explanation": explanation,
            })

    cur.close()
    conn.close()
    patterns.sort(key=lambda p: p["affectedSupplierCount"], reverse=True)
    return patterns


def _generate_pattern_explanation(cause_label: str, supplier_names: list, incident_count: int) -> str:
    prompt = f"""Write ONE short sentence (max 30 words) flagging a potential systemic supply \
chain pattern for a procurement dashboard. Be factual, no headers.

Pattern category: {cause_label}
Affected suppliers ({len(supplier_names)}): {', '.join(supplier_names)}
Total related incidents: {incident_count}
"""
    try:
        response = requests.post(OLLAMA_URL, json={
            "model": OLLAMA_MODEL, "prompt": prompt, "stream": False,
        }, timeout=60)
        response.raise_for_status()
        return response.json()["response"].strip()
    except Exception:
        return (f"{len(supplier_names)} suppliers ({', '.join(supplier_names)}) show "
                f"{incident_count} incidents linked to '{cause_label}' in the last "
                f"{PATTERN_WINDOW_DAYS} days — may indicate a shared external cause "
                f"rather than individual supplier issues.")


if __name__ == "__main__":
    print("Detecting cross-supplier patterns...\n")
    patterns = detect_systemic_patterns()
    if not patterns:
        print("No systemic patterns detected (no cause affects 2+ distinct suppliers).")
    for p in patterns:
        print(f"{p['causeCategory']} — {p['affectedSupplierCount']} suppliers, "
              f"{p['totalIncidents']} incidents")
        print(f"  Affected: {', '.join(p['affectedSuppliers'])}")
        print(f"  {p['explanation']}\n")
