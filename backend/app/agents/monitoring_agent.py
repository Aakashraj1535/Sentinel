"""
Monitoring & Detection Agent
-----------------------------
Deliberately rule-based, NOT LLM-based — this step just compares dates and
computes a severity score. Fast, deterministic, 100% explainable.

Logic:
  1. Scan orders table for delayed / overdue shipments.
  2. Compute how many days late (or overdue-so-far, if still in transit).
  3. Compute a severity score from delay length + order quantity.
  4. Write a new row into `exceptions` for each newly-detected problem
     (skips orders that already have an exception recorded).

Run standalone for testing:  python -m app.agents.monitoring_agent
"""

from datetime import datetime, timezone
import uuid

from app.db import get_connection, get_dict_cursor


def _generate_exception_id() -> str:
    """
    Short, human-readable ID in the existing 'EX-XXXXX' style, but sourced
    from uuid4 instead of random.randint — practically collision-free,
    unlike the previous 90,000-value random range which could eventually
    collide and abort the whole detection batch before it commits.
    """
    return f"EX-{uuid.uuid4().hex[:8].upper()}"


SEVERITY_THRESHOLDS = {
    "Low": 3,
    "Medium": 7,
    # anything above Medium's ceiling -> High
}


def compute_severity_score(delay_days: float, quantity: int) -> float:
    """
    Simple weighted formula — NOT machine learning, intentionally.
    Delay length matters most; larger orders raise the stakes slightly.
    """
    delay_component = delay_days * 1.2
    quantity_component = min(quantity / 500, 3.0)  # cap influence of huge orders
    return round(delay_component + quantity_component, 2)


def severity_label(score: float) -> str:
    if score <= SEVERITY_THRESHOLDS["Low"]:
        return "Low"
    elif score <= SEVERITY_THRESHOLDS["Medium"]:
        return "Medium"
    return "High"


def detect_exceptions():
    """
    Scans orders for delays not yet turned into an exception record.
    Returns a list of newly created exception dicts.
    """
    conn = get_connection()
    cur = get_dict_cursor(conn)

    # Find delayed orders that don't already have an exception logged
    cur.execute("""
        SELECT o.id AS order_id, o.supplier_id, o.item, o.quantity,
               o.expected_delivery, o.actual_delivery, o.status
        FROM orders o
        WHERE o.status IN ('delayed', 'pending')
          AND NOT EXISTS (
              SELECT 1 FROM exceptions e WHERE e.order_id = o.id
          )
    """)
    candidates = cur.fetchall()

    new_exceptions = []
    now = datetime.now(timezone.utc)

    for row in candidates:
        expected = row["expected_delivery"]
        actual = row["actual_delivery"]

        if actual is not None:
            delay_days = (actual - expected).total_seconds() / 86400
        else:
            # Still in transit — only flag if already overdue
            delay_days = (now - expected).total_seconds() / 86400

        if delay_days <= 0:
            continue  # not actually late, skip

        score = compute_severity_score(delay_days, row["quantity"])
        severity = severity_label(score)

        exception_id = _generate_exception_id()
        try:
            cur.execute("""
                INSERT INTO exceptions (id, order_id, supplier_id, exception_type,
                                         severity, status, detected_at)
                VALUES (%s, %s, %s, %s, %s, 'Active', %s)
            """, (exception_id, row["order_id"], row["supplier_id"], "Shipment Delay",
                  severity, now))

            cur.execute("""
                INSERT INTO audit_log (exception_id, step, summary)
                VALUES (%s, 'Detected', %s)
            """, (exception_id,
                  f"Order {row['order_id']} is {delay_days:.1f} days late "
                  f"(quantity: {row['quantity']}). Severity: {severity} "
                  f"(score: {score})."))

            # Commit per-row (not once at the end): if a later row in this
            # batch fails, everything already inserted so far still sticks,
            # instead of a single failure wiping out the whole batch.
            conn.commit()
        except Exception as e:
            # Extremely unlikely with uuid4-derived IDs, but don't let one bad
            # insert abort the whole detection batch (and lose every other
            # newly-detected exception along with it).
            print(f"[monitoring_agent] Failed to insert exception for order "
                  f"{row['order_id']}: {e}")
            conn.rollback()
            continue

        new_exceptions.append({
            "id": exception_id,
            "order_id": row["order_id"],
            "supplier_id": row["supplier_id"],
            "exception_type": "Shipment Delay",
            "severity": severity,
            "delay_days": round(delay_days, 1),
        })

    cur.close()
    conn.close()
    return new_exceptions


if __name__ == "__main__":
    results = detect_exceptions()
    print(f"Detected {len(results)} new exceptions:\n")
    for r in results:
        print(f"  {r['id']} | {r['supplier_id']} | {r['exception_type']} | "
              f"Severity: {r['severity']} | {r['delay_days']} days late")
