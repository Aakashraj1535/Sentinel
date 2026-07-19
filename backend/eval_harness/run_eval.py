"""
Evaluation Harness for Supply Chain Sentinel
=============================================
Run this from inside your scs-backend folder, with venv active and both
your FastAPI server (port 8000) and Ollama running.

USAGE:
    python eval_harness/run_eval.py

WHAT IT DOES:
1. Fills in human_expected_escalate for you to answer FIRST (before seeing
   system output -- this prevents you from unconsciously matching your
   judgment to what the system did).
2. Cleans up any previous EVAL-* test data.
3. Inserts 20 synthetic delayed orders (see scenarios.json).
4. Calls /api/run-pipeline to let your real agents process them.
5. Reads back what the system decided (severity, confidence, escalated).
6. Computes a simple baseline rule for comparison (escalate if delay > 3 days).
7. Scores your system against your human judgment, and the baseline against
   your human judgment, and prints/saves a comparison report.

OUTPUT:
    eval_harness/results.csv  -- full row-by-row results
    Printed summary stats in the terminal
"""

import json
import sys
import time
import requests
from pathlib import Path
from datetime import datetime, timedelta, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # so "app" is importable

from app.db import get_connection, get_dict_cursor  # noqa: E402

SCENARIOS_PATH = Path(__file__).parent / "scenarios.json"
RESULTS_PATH = Path(__file__).parent / "results.csv"
API_BASE = "http://localhost:8000"


# ---- Same severity formula as monitoring_agent.py, kept in sync manually ----
def compute_expected_severity(delay_days: float, quantity: int) -> tuple[float, str]:
    delay_component = delay_days * 1.2
    quantity_component = min(quantity / 500, 3.0)
    score = round(delay_component + quantity_component, 2)
    if score <= 3:
        label = "Low"
    elif score <= 7:
        label = "Medium"
    else:
        label = "High"
    return score, label


def baseline_escalate(delay_days: float) -> bool:
    """Naive baseline: escalate anything delayed more than 3 days. No LLM, no context."""
    return delay_days > 3


def load_scenarios() -> list[dict]:
    with open(SCENARIOS_PATH) as f:
        return json.load(f)


def collect_human_labels(scenarios: list[dict]) -> list[dict]:
    """If human_expected_escalate is still null, ask the user to fill it in now,
    BEFORE running the system, to keep the judgment unbiased."""
    missing = [s for s in scenarios if s["human_expected_escalate"] is None]
    if not missing:
        print("All scenarios already have human_expected_escalate filled in. Skipping.")
        return scenarios

    print("\n" + "=" * 70)
    print("BLIND LABELING STEP")
    print("For each scenario below, decide (based on YOUR domain judgment,")
    print("not the code): should this be escalated to a human, or is it")
    print("safe for the system to auto-resolve? Answer y/n.")
    print("=" * 70 + "\n")

    for s in missing:
        score, sev = compute_expected_severity(s["delay_days"], s["quantity"])
        print(f"\n{s['scenario_id']}: Supplier {s['supplier_id']} ({s['doc_richness']} docs)")
        print(f"  Delay: {s['delay_days']} days | Quantity: {s['quantity']} | "
              f"Computed severity: {sev} (score={score})")
        print(f"  Note: {s['notes']}")
        while True:
            ans = input("  Should this escalate to a human? (y/n): ").strip().lower()
            if ans in ("y", "n"):
                s["human_expected_escalate"] = (ans == "y")
                break
            print("  Please type y or n.")

    with open(SCENARIOS_PATH, "w") as f:
        json.dump(scenarios, f, indent=2)
    print("\nSaved your labels back to scenarios.json.\n")
    return scenarios


def _find_dependent_tables(cur, target_table: str, target_col: str = "id"):
    """Find all tables + columns that have a foreign key pointing at target_table.target_col."""
    cur.execute("""
        SELECT tc.table_name, kcu.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage ccu
          ON tc.constraint_name = ccu.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY'
          AND ccu.table_name = %s
          AND ccu.column_name = %s
    """, (target_table, target_col))
    return cur.fetchall()


def cleanup_previous_run(cur, conn):
    try:
        # Delete anything that references exceptions for our EVAL orders first
        dependents = _find_dependent_tables(cur, "exceptions", "id")
        for dep in dependents:
            table, col = dep["table_name"], dep["column_name"]
            cur.execute(f"""
                DELETE FROM {table}
                WHERE {col} IN (
                    SELECT id FROM exceptions WHERE order_id LIKE 'EVAL-%%'
                )
            """)
        cur.execute("DELETE FROM exceptions WHERE order_id LIKE 'EVAL-%%'")
        cur.execute("DELETE FROM orders WHERE id LIKE 'EVAL-%%'")
        conn.commit()
        print("Cleaned up any previous EVAL-* test data.")
    except Exception as e:
        conn.rollback()
        print(f"Cleanup hit an issue, rolled back: {e}")
        print("If this repeats, tell Claude the table/column names shown above.")
        raise


def insert_scenarios(cur, conn, scenarios: list[dict]):
    now = datetime.now(timezone.utc)
    expected_base = now - timedelta(days=30)  # arbitrary fixed anchor in the past

    for s in scenarios:
        expected_delivery = expected_base
        actual_delivery = expected_base + timedelta(days=s["delay_days"])
        cur.execute("""
            INSERT INTO orders (id, supplier_id, item, quantity, warehouse_id,
                                 expected_delivery, actual_delivery, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'delayed')
        """, (
            s["scenario_id"], s["supplier_id"], "Eval Test Item", s["quantity"],
            s["warehouse_id"], expected_delivery, actual_delivery
        ))
    conn.commit()
    print(f"Inserted {len(scenarios)} synthetic test orders.")


def run_pipeline():
    print("Calling /api/run-pipeline ... (this triggers detection + RAG + LLM resolution, may take a minute)")
    resp = requests.post(f"{API_BASE}/api/run-pipeline", timeout=300)
    resp.raise_for_status()
    data = resp.json()
    print(f"Pipeline processed {data.get('processed')} exception(s).")
    return data


def fetch_results(cur, scenarios: list[dict]) -> list[dict]:
    rows = []
    for s in scenarios:
        cur.execute("""
            SELECT e.id AS exception_id, e.severity, e.auto_resolved, e.escalation_reason
            FROM exceptions e
            WHERE e.order_id = %s
        """, (s["scenario_id"],))
        exc = cur.fetchone()

        if exc is None:
            rows.append({**s, "system_severity": None, "system_escalated": None,
                         "confidence_pct": None, "escalation_reason": None,
                         "note": "NO EXCEPTION CREATED - check monitoring_agent / order status"})
            continue

        cur.execute("""
            SELECT confidence_pct FROM recommendations
            WHERE exception_id = %s ORDER BY rank ASC LIMIT 1
        """, (exc["exception_id"],))
        rec = cur.fetchone()
        confidence = float(rec["confidence_pct"]) if rec and rec["confidence_pct"] is not None else None

        rows.append({
            **s,
            "system_severity": exc["severity"],
            "system_escalated": (not exc["auto_resolved"]),
            "confidence_pct": confidence,
            "escalation_reason": exc["escalation_reason"],
        })
    return rows


def score_and_report(rows: list[dict]):
    import csv

    for r in rows:
        score, expected_sev = compute_expected_severity(r["delay_days"], r["quantity"])
        r["expected_severity"] = expected_sev
        r["severity_match"] = (r["system_severity"] == expected_sev)
        r["baseline_escalate"] = baseline_escalate(r["delay_days"])
        r["system_agrees_with_human"] = (r["system_escalated"] == r["human_expected_escalate"])
        r["baseline_agrees_with_human"] = (r["baseline_escalate"] == r["human_expected_escalate"])

    fieldnames = ["scenario_id", "supplier_id", "doc_richness", "quantity", "delay_days",
                  "expected_severity", "system_severity", "severity_match",
                  "confidence_pct", "system_escalated", "baseline_escalate",
                  "human_expected_escalate", "system_agrees_with_human",
                  "baseline_agrees_with_human", "escalation_reason", "notes"]

    with open(RESULTS_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    total = len(rows)
    valid = [r for r in rows if r["system_severity"] is not None]

    sev_acc = sum(1 for r in valid if r["severity_match"]) / len(valid) * 100 if valid else 0
    sys_agree = sum(1 for r in valid if r["system_agrees_with_human"]) / len(valid) * 100 if valid else 0
    base_agree = sum(1 for r in valid if r["baseline_agrees_with_human"]) / len(valid) * 100 if valid else 0

    print("\n" + "=" * 70)
    print("EVALUATION SUMMARY")
    print("=" * 70)
    print(f"Total scenarios: {total}  |  Successfully processed: {len(valid)}")
    print(f"\nSeverity accuracy (system vs formula):         {sev_acc:.1f}%")
    print(f"Escalation agreement (SYSTEM vs your judgment): {sys_agree:.1f}%")
    print(f"Escalation agreement (BASELINE vs your judgment): {base_agree:.1f}%")
    print(f"  -> Your multi-agent system {'beats' if sys_agree > base_agree else 'does NOT beat'} "
          f"the naive baseline by {abs(sys_agree - base_agree):.1f} points")

    print("\nAverage confidence by documentation richness:")
    for group in ["rich", "medium", "contract_only", "none"]:
        confs = [r["confidence_pct"] for r in valid if r["doc_richness"] == group and r["confidence_pct"] is not None]
        if confs:
            avg = sum(confs) / len(confs)
            print(f"  {group:15s}: avg confidence {avg:.1f}%  (n={len(confs)})")
        else:
            print(f"  {group:15s}: no data")

    print(f"\nFull results saved to: {RESULTS_PATH}")
    print("=" * 70 + "\n")


def main():
    scenarios = load_scenarios()
    scenarios = collect_human_labels(scenarios)

    conn = get_connection()
    cur = get_dict_cursor(conn)

    cleanup_previous_run(cur, conn)
    insert_scenarios(cur, conn, scenarios)

    run_pipeline()
    time.sleep(2)  # small buffer in case of async writes

    rows = fetch_results(cur, scenarios)
    score_and_report(rows)

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
