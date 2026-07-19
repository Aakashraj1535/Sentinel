"""
Resolution Agent
-----------------
Takes an exception + its retrieved context (from the RAG agent) and asks the
local LLM (via Ollama) to generate 2-3 ranked resolution options, each with
a confidence score. Also applies the escalation rule: low confidence or high
severity -> flag for human review instead of trusting the AI blindly.

Requires Ollama running locally with a model pulled, e.g.:
    ollama pull llama3.2

Run standalone for testing:  python -m app.agents.resolution_agent
"""

import json
import re
import requests

from app.db import get_connection, get_dict_cursor
from app.agents.rag_agent import retrieve_context

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2"

# --- Escalation thresholds (tune these as you like) ---
CONFIDENCE_ESCALATION_THRESHOLD = 60   # below this -> escalate
HIGH_SEVERITY_CONFIDENCE_FLOOR = 75    # High severity needs even more confidence to auto-resolve


def build_prompt(exception: dict, context_docs: list, supplier: dict) -> str:
    context_text = "\n".join(
        f"- [{d['doc_kind']} | {d['doc_label']} | {d['relevance']}] {d['chunk_text']}"
        for d in context_docs
    ) or "No relevant documents were retrieved."

    return f"""You are a supply chain resolution assistant. Analyze the exception below \
using ONLY the retrieved context provided. Do not invent facts not present in the context.

EXCEPTION:
Type: {exception['exception_type']}
Severity: {exception['severity']}
Supplier: {supplier['name']} ({supplier['id']})
Supplier on-time rate: {supplier['on_time_rate']}%
Supplier total past incidents: {supplier['total_incidents']}

RETRIEVED CONTEXT:
{context_text}

TASK:
Suggest 2-3 ranked resolution actions. For each, give a short action description,
an estimated cost (Low/Medium/High), an estimated delivery/resolution time,
the likely customer impact (Minimal/Moderate/Significant), a confidence score
from 0-100 (how sure you are this is the right action given the context), and
a one-sentence root cause summary shared across all options.

Respond with ONLY valid JSON in exactly this shape, no other text:
{{
  "root_cause": "one sentence summary",
  "options": [
    {{"action": "...", "estimated_cost": "Low|Medium|High", "estimated_delivery": "...",
      "customer_impact": "Minimal|Moderate|Significant", "confidence_pct": 0}}
  ]
}}
"""


def _extract_json(raw_text: str) -> dict:
    """LLMs sometimes wrap JSON in markdown fences or add stray text. Extract robustly."""
    raw_text = raw_text.strip()
    # Strip markdown code fences if present
    raw_text = re.sub(r"^```(json)?", "", raw_text).strip()
    raw_text = re.sub(r"```$", "", raw_text).strip()
    # If there's still leading/trailing junk, grab the outermost {...}
    match = re.search(r"\{.*\}", raw_text, re.DOTALL)
    if match:
        raw_text = match.group(0)
    return json.loads(raw_text)


def call_ollama(prompt: str) -> dict:
    response = requests.post(OLLAMA_URL, json={
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json",  # ask Ollama to constrain output to valid JSON
    }, timeout=120)
    response.raise_for_status()
    raw_output = response.json()["response"]
    return _extract_json(raw_output)


def confidence_label(pct: float) -> str:
    if pct >= 75:
        return "High"
    elif pct >= 50:
        return "Medium"
    return "Low"


def resolve_exception(exception_id: str, context_docs: list = None):
    conn = get_connection()
    cur = get_dict_cursor(conn)

    cur.execute("SELECT * FROM exceptions WHERE id = %s", (exception_id,))
    exception = cur.fetchone()
    if not exception:
        cur.close()
        conn.close()
        raise ValueError(f"Exception {exception_id} not found")

    cur.execute("SELECT * FROM suppliers WHERE id = %s", (exception["supplier_id"],))
    supplier = cur.fetchone()

    if context_docs is None:
        context_docs = retrieve_context(exception_id, top_k=5)
    prompt = build_prompt(exception, context_docs, supplier)

    try:
        result = call_ollama(prompt)
    except Exception as e:
        cur.close()
        conn.close()
        raise RuntimeError(
            f"Ollama call failed ({e}). Is Ollama running? Try: ollama serve"
        ) from e

    options = result.get("options", [])[:3]
    root_cause = result.get("root_cause", "Not determined.")

    max_confidence = max((o.get("confidence_pct", 0) for o in options), default=0)

    escalate = max_confidence < CONFIDENCE_ESCALATION_THRESHOLD or (
        exception["severity"] == "High" and max_confidence < HIGH_SEVERITY_CONFIDENCE_FLOOR
    )
    escalation_reason = None
    if escalate:
        if max_confidence < CONFIDENCE_ESCALATION_THRESHOLD:
            escalation_reason = f"Confidence ({max_confidence}%) below threshold ({CONFIDENCE_ESCALATION_THRESHOLD}%)"
        else:
            escalation_reason = f"High severity requires confidence >= {HIGH_SEVERITY_CONFIDENCE_FLOOR}%"

    # Clear any previous recommendations for this exception (safe to re-run)
    cur.execute("DELETE FROM recommendations WHERE exception_id = %s", (exception_id,))

    for i, opt in enumerate(options, start=1):
        conf_pct = opt.get("confidence_pct", 0)
        cur.execute("""
            INSERT INTO recommendations
                (exception_id, rank, action, estimated_cost, estimated_delivery,
                 customer_impact, confidence_pct, confidence_level)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (exception_id, i, opt.get("action", ""), opt.get("estimated_cost", ""),
              opt.get("estimated_delivery", ""), opt.get("customer_impact", ""),
              conf_pct, confidence_label(conf_pct)))

    new_status = "Escalated" if escalate else "Resolved"
    cur.execute("""
        UPDATE exceptions
        SET root_cause = %s, auto_resolved = %s, escalation_reason = %s, status = %s
        WHERE id = %s
    """, (root_cause, not escalate, escalation_reason, new_status, exception_id))

    cur.execute("""
        INSERT INTO audit_log (exception_id, step, summary)
        VALUES (%s, 'Recommended', %s)
    """, (exception_id, f"Generated {len(options)} option(s), max confidence {max_confidence}%."))

    cur.execute("""
        INSERT INTO audit_log (exception_id, step, summary)
        VALUES (%s, 'Decided', %s)
    """, (exception_id, f"Status set to {new_status}."
          + (f" Reason: {escalation_reason}" if escalation_reason else "")))

    conn.commit()
    cur.close()
    conn.close()

    return {
        "exception_id": exception_id,
        "root_cause": root_cause,
        "options": options,
        "status": new_status,
        "escalation_reason": escalation_reason,
    }


if __name__ == "__main__":
    conn = get_connection()
    cur = get_dict_cursor(conn)
    cur.execute("SELECT id FROM exceptions WHERE status = 'Active' ORDER BY id LIMIT 1")
    sample = cur.fetchone()
    cur.close()
    conn.close()

    if not sample:
        print("No active exceptions found — run the monitoring agent first.")
    else:
        exc_id = sample["id"]
        print(f"Resolving {exc_id} (this calls your local Ollama model, may take a moment)...\n")
        result = resolve_exception(exc_id)
        print(f"Root cause: {result['root_cause']}\n")
        for i, opt in enumerate(result["options"], start=1):
            print(f"Option {i}: {opt.get('action')}")
            print(f"  Cost: {opt.get('estimated_cost')} | "
                  f"Time: {opt.get('estimated_delivery')} | "
                  f"Impact: {opt.get('customer_impact')} | "
                  f"Confidence: {opt.get('confidence_pct')}%")
        print(f"\nFinal status: {result['status']}")
        if result["escalation_reason"]:
            print(f"Escalation reason: {result['escalation_reason']}")
