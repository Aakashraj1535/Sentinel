"""
Demo Data Seeder for Supply Chain Sentinel
============================================
Run this before every rehearsal / the actual panel demo to reset the
database into a realistic, story-driven state that shows off every agent.

USAGE:
    python eval_harness/demo_seed.py

Requires your FastAPI server (port 8000) and Ollama both running.

WHAT IT CREATES:
  - A cross-supplier pattern (3 suppliers, "customs delay") for the
    Pattern Detection Agent to surface.
  - A "Rising Risk" supplier (Norlink) and an "Improving" supplier
    (Meridian) for the Predictive Risk Agent.
  - One guaranteed Escalated exception (Delta Rivers) ready for you to
    click Approve/Reject on, for the human-in-the-loop demo.
  - 4 fresh live orders run through the REAL pipeline (LLM calls), so
    you have current-day activity to show, including one deliberately
    undocumented/high-severity case that ties back to your evaluation
    findings as a talking point.

This is SAFE TO RE-RUN — it always cleans up its own previous demo data
first (anything tagged DEMO-*).
"""

import sys
import time
import requests
from pathlib import Path
from datetime import datetime, timedelta, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import get_connection, get_dict_cursor  # noqa: E402

API_BASE = "http://localhost:8000"


def _find_dependent_tables(cur, target_table: str, target_col: str = "id"):
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


def reset_demo_data(cur, conn):
    try:
        dependents = _find_dependent_tables(cur, "exceptions", "id")
        for dep in dependents:
            table, col = dep["table_name"], dep["column_name"]
            cur.execute(f"""
                DELETE FROM {table}
                WHERE {col} IN (
                    SELECT id FROM exceptions
                    WHERE id LIKE 'DEMO-HIST-%%'
                       OR order_id LIKE 'DEMO-ORD-%%'
                )
            """)
        cur.execute("""
            DELETE FROM exceptions
            WHERE id LIKE 'DEMO-HIST-%%' OR order_id LIKE 'DEMO-ORD-%%'
        """)
        cur.execute("DELETE FROM orders WHERE id LIKE 'DEMO-ORD-%%'")
        conn.commit()
        print("Reset any previous demo data.")
    except Exception as e:
        conn.rollback()
        print(f"Reset hit an issue, rolled back: {e}")
        raise


def days_ago(n):
    return datetime.now(timezone.utc) - timedelta(days=n)


def insert_historical_exception(cur, exc_id, supplier_id, exception_type, severity,
                                 status, detected_at, root_cause, auto_resolved,
                                 escalation_reason, confidence_pct):
    cur.execute("""
        INSERT INTO exceptions (id, order_id, supplier_id, exception_type, severity,
                                 status, detected_at, root_cause, auto_resolved,
                                 escalation_reason)
        VALUES (%s, NULL, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (exc_id, supplier_id, exception_type, severity, status, detected_at,
          root_cause, auto_resolved, escalation_reason))

    cur.execute("""
        INSERT INTO recommendations (exception_id, rank, action, estimated_cost,
                                      estimated_delivery, customer_impact,
                                      confidence_pct, confidence_level)
        VALUES (%s, 1, %s, 'Medium', '3-5 days', 'Moderate', %s, %s)
    """, (exc_id, f"Coordinate with supplier on {exception_type.lower()} resolution.",
          confidence_pct, "High" if confidence_pct >= 75 else "Medium" if confidence_pct >= 50 else "Low"))

    cur.execute("""
        INSERT INTO audit_log (exception_id, step, timestamp, summary)
        VALUES (%s, 'detected', %s, %s)
    """, (exc_id, detected_at, f"Exception detected: {root_cause}"))
    cur.execute("""
        INSERT INTO audit_log (exception_id, step, timestamp, summary)
        VALUES (%s, 'resolved', %s, %s)
    """, (exc_id, detected_at + timedelta(hours=1),
          f"{'Escalated for human review' if status == 'Escalated' else 'Auto-resolved'}."))


def seed_historical_data(cur, conn):
    print("Seeding historical data (pattern detection + predictive risk)...")

    # --- Cross-supplier pattern: "customs delay" across 3 different suppliers ---
    pattern_suppliers = [
        ("SUP-003", "DEMO-HIST-P1", 14),
        ("SUP-007", "DEMO-HIST-P2", 9),
        ("SUP-005", "DEMO-HIST-P3", 5),
    ]
    for supplier_id, exc_id, days_back in pattern_suppliers:
        insert_historical_exception(
            cur, exc_id, supplier_id, "Customs Hold", "Medium", "Resolved",
            days_ago(days_back),
            root_cause=f"Shipment held at customs pending documentation review, causing delay.",
            auto_resolved=True, escalation_reason=None, confidence_pct=82.0
        )

    # --- Rising risk: Norlink (SUP-006), 2 exceptions in last 14 days, none before ---
    rising_exceptions = [("DEMO-HIST-R1", 9), ("DEMO-HIST-R2", 3)]
    for exc_id, days_back in rising_exceptions:
        insert_historical_exception(
            cur, exc_id, "SUP-006", "Shipment Delay", "Medium", "Resolved",
            days_ago(days_back),
            root_cause="Carrier capacity shortage caused delivery delay.",
            auto_resolved=True, escalation_reason=None, confidence_pct=80.0
        )

    # --- Improving: Meridian (SUP-001), 3 exceptions 18-25 days ago, none recently ---
    improving_exceptions = [("DEMO-HIST-I1", 25), ("DEMO-HIST-I2", 22), ("DEMO-HIST-I3", 18)]
    for exc_id, days_back in improving_exceptions:
        insert_historical_exception(
            cur, exc_id, "SUP-001", "Shipment Delay", "Low", "Resolved",
            days_ago(days_back),
            root_cause="Minor scheduling delay, resolved quickly with no recurrence.",
            auto_resolved=True, escalation_reason=None, confidence_pct=88.0
        )

    # --- Guaranteed escalated exception: Delta Rivers (SUP-008) ---
    insert_historical_exception(
        cur, "DEMO-HIST-ESC1", "SUP-008", "Quality Issue", "High", "Escalated",
        days_ago(1),
        root_cause="Incoming batch failed quality inspection; root cause unclear from available context.",
        auto_resolved=False,
        escalation_reason="Confidence (45%) below threshold (60%)",
        confidence_pct=45.0
    )

    conn.commit()
    print("Historical data seeded: 3-supplier customs pattern, Rising (Norlink), "
          "Improving (Meridian), 1 guaranteed Escalated exception (Delta Rivers).")


def refresh_predictive_risk():
    print("Refreshing predictive risk forecasts...")
    resp = requests.post(f"{API_BASE}/api/predictive-risk/refresh", timeout=60)
    resp.raise_for_status()
    print("Predictive risk refreshed.")


def insert_live_orders(cur, conn):
    live_orders = [
        ("DEMO-ORD-001", "SUP-002", 100, 1, "WH-A (Chennai)"),   # rich docs, clean auto-resolve
        ("DEMO-ORD-002", "SUP-004", 500, 5, "WH-B (Coimbatore)"),  # medium docs, moderate
        ("DEMO-ORD-003", "SUP-9B4530", 800, 8, "WH-C (Bengaluru)"),  # no docs, high severity - talking point
        ("DEMO-ORD-004", "SUP-006", 300, 3, "WH-D (Hyderabad)"),  # ties back to Rising Risk supplier
    ]
    now = datetime.now(timezone.utc)
    expected_base = now - timedelta(days=1)  # "yesterday" so it reads as freshly overdue

    for order_id, supplier_id, qty, delay_days, warehouse in live_orders:
        expected_delivery = expected_base
        actual_delivery = expected_base + timedelta(days=delay_days)
        cur.execute("""
            INSERT INTO orders (id, supplier_id, item, quantity, warehouse_id,
                                 expected_delivery, actual_delivery, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'delayed')
        """, (order_id, supplier_id, "Demo Item", qty, warehouse,
              expected_delivery, actual_delivery))
    conn.commit()
    print(f"Inserted {len(live_orders)} live orders for real pipeline processing.")


def run_pipeline():
    print("Calling /api/run-pipeline for live orders (this calls the LLM 4 times, may take a minute)...")
    resp = requests.post(f"{API_BASE}/api/run-pipeline", timeout=300)
    resp.raise_for_status()
    data = resp.json()
    print(f"Pipeline processed {data.get('processed')} live exception(s).")


def main():
    conn = get_connection()
    cur = get_dict_cursor(conn)

    reset_demo_data(cur, conn)
    seed_historical_data(cur, conn)
    refresh_predictive_risk()
    insert_live_orders(cur, conn)
    run_pipeline()

    print("\n" + "=" * 70)
    print("DEMO DATA READY")
    print("=" * 70)
    print("Talking points to hit during your demo:")
    print("  1. Dashboard: mix of auto-resolved and escalated exceptions")
    print("  2. Human-in-the-loop: 'Delta Rivers Trading' exception is Escalated")
    print("     -> click Approve/Reject on it live")
    print("  3. Predictive Risk: 'Norlink Distribution' should show Rising,")
    print("     'Meridian Logistics' should show Improving")
    print("  4. Pattern Detection: Horizon, Pinecrest, and Crestline should")
    print("     all show up under a 'Customs Hold' systemic pattern")
    print("  5. Talking point on limitations: the 'Kumar' (SUP-9B4530) order")
    print("     has zero documentation but still auto-resolved with high")
    print("     confidence -- this is the exact finding from your evaluation")
    print("     harness, showing you understand your own system's limits.")
    print("=" * 70)

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
