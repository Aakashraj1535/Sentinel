"""
Create a test exception at a chosen severity, for demos and manual
testing of downstream features (SLA badges, Slack/email notifications,
the Human Review panel, etc.) without waiting for real order data to
naturally become overdue.

USAGE:
    python create_test_exception.py high
    python create_test_exception.py medium
    python create_test_exception.py low
    python create_test_exception.py high --supplier SUP-003

By default a RANDOM supplier is picked each run (so repeated demo runs
show variety instead of always hitting the same one). Pass --supplier
<id> to pin a specific one, or --list-suppliers to see the available IDs.

By default the exception is backdated far enough into the past that it's
ALREADY SLA-breached the moment it's created -- useful for immediately
testing the SLA monitor / Slack / email notification path on the very
next scheduler tick, instead of waiting hours for a real breach.

Use --fresh to instead create one that's brand new (0 hours old, status
On Track) -- useful for testing the Human Review panel / approve-reject
flow on a clean, non-urgent exception, or for showing the "happy path"
in a demo.

This creates a real order + exception row via direct SQL (not through the
LLM pipeline), so it does NOT require Ollama to be running. It does NOT
go through resolution_agent, so it won't have an AI recommendation
attached -- if you want one, run:
    curl -X POST -H "X-User-Role: Procurement Manager" http://localhost:8080/api/run-pipeline
afterward, once Ollama is up, to have the pipeline pick it up and process it
(it'll show status='Active' until then, exactly like a normal new detection).

SAFE TO RUN REPEATEDLY -- each run creates a new, uniquely-IDed order and
exception; nothing is overwritten or deleted.
"""

import random
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.db import get_connection, get_dict_cursor  # noqa: E402
from app.sla import sla_hours_for_severity  # noqa: E402

VALID_SEVERITIES = {"high": "High", "medium": "Medium", "low": "Low"}

# How far past the SLA deadline to backdate a non---fresh test exception,
# so it's unambiguously already breached (not just barely, in case of
# clock skew) the moment it's created.
BREACH_OVERSHOOT_HOURS = 1


def _pick_supplier(cur, requested_id: str = None) -> dict:
    if requested_id:
        cur.execute("SELECT id, name FROM suppliers WHERE id = %s", (requested_id,))
        supplier = cur.fetchone()
        if not supplier:
            print(f"ERROR: no supplier with id '{requested_id}'. "
                  f"Run with --list-suppliers to see valid IDs.")
            sys.exit(1)
        return supplier

    cur.execute("SELECT id, name FROM suppliers")
    suppliers = cur.fetchall()
    if not suppliers:
        print("ERROR: no suppliers found in the database. Seed suppliers first.")
        sys.exit(1)
    return random.choice(suppliers)


def main():
    args = sys.argv[1:]
    fresh = "--fresh" in args
    args = [a for a in args if a != "--fresh"]

    if "--list-suppliers" in args:
        conn = get_connection()
        cur = get_dict_cursor(conn)
        cur.execute("SELECT id, name, region FROM suppliers ORDER BY name")
        for s in cur.fetchall():
            print(f"  {s['id']:<10} {s['name']} ({s['region']})")
        cur.close()
        conn.close()
        sys.exit(0)

    requested_supplier = None
    if "--supplier" in args:
        idx = args.index("--supplier")
        if idx + 1 >= len(args):
            print("ERROR: --supplier requires a value, e.g. --supplier SUP-003")
            sys.exit(1)
        requested_supplier = args[idx + 1]
        args = args[:idx] + args[idx + 2:]

    if len(args) != 1 or args[0].lower() not in VALID_SEVERITIES:
        print(__doc__)
        print(f"ERROR: expected one of {list(VALID_SEVERITIES)} as the severity argument.")
        sys.exit(1)

    severity = VALID_SEVERITIES[args[0].lower()]

    conn = get_connection()
    cur = get_dict_cursor(conn)

    supplier = _pick_supplier(cur, requested_supplier)

    suffix = uuid.uuid4().hex[:6].upper()
    order_id = f"PO-TEST-{suffix}"
    exception_id = f"EX-TEST{suffix}"

    if fresh:
        detected_at = datetime.now(timezone.utc)
        delay_hours = 2  # just barely late, for a realistic-looking order
    else:
        hours = sla_hours_for_severity(severity) + BREACH_OVERSHOOT_HOURS
        detected_at = datetime.now(timezone.utc) - timedelta(hours=hours)
        delay_hours = hours

    expected_delivery = detected_at - timedelta(hours=delay_hours)

    try:
        cur.execute("""
            INSERT INTO orders (id, supplier_id, item, quantity, warehouse_id,
                                 expected_delivery, status)
            VALUES (%s, %s, %s, %s, %s, %s, 'delayed')
        """, (order_id, supplier["id"], "Test Widget (demo)", 100, "WH-TEST",
              expected_delivery))

        cur.execute("""
            INSERT INTO exceptions (id, order_id, supplier_id, exception_type,
                                     severity, status, detected_at)
            VALUES (%s, %s, %s, 'Shipment Delay', %s, 'Active', %s)
        """, (exception_id, order_id, supplier["id"], severity, detected_at))

        cur.execute("""
            INSERT INTO audit_log (exception_id, step, summary)
            VALUES (%s, 'Detected', %s)
        """, (exception_id,
              f"[TEST DATA] Manually created {severity} severity exception "
              f"for supplier {supplier['name']} via create_test_exception.py."))

        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"ERROR: {e}")
        sys.exit(1)
    finally:
        cur.close()
        conn.close()

    print(f"Created exception {exception_id} (severity: {severity})")
    print(f"  Order: {order_id} | Supplier: {supplier['name']} ({supplier['id']})")
    if fresh:
        print("  SLA status: On Track (just detected)")
    else:
        print(f"  SLA status: Already BREACHED ({delay_hours}h past deadline)")
        print("  -> Should trigger a notification on the next scheduler tick "
              "(runs every few minutes) if email/Slack are configured.")
    print(f"\nView it at: http://localhost:5173/exceptions/{exception_id}")


if __name__ == "__main__":
    main()
