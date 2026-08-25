"""
Backfill: financial impact for pre-existing exceptions
----------------------------------------------------------
Why this exists: the financial impact step (estimate_financial_impact)
only runs automatically as part of the LangGraph pipeline
(retrieve -> resolve -> estimate_impact -> report) for exceptions that
flow through it AFTER this feature was added. Any exception detected
before that -- Active, Escalated, or already Resolved -- never had this
step run on it and has no estimate.

Re-running the FULL pipeline on old exceptions would be wasteful (it
re-calls the LLM for resolution options too) and risks changing an
exception's status/decision history. This script calls ONLY
estimate_financial_impact() directly for every exception that doesn't
have one yet -- it touches nothing except the financial_impact_* columns
and an audit_log entry, regardless of the exception's current status.

Run:  python -m db.backfill_financial_impact
Safe to re-run -- only processes exceptions where
financial_impact_computed_at IS NULL.
"""

from app.db import get_connection, get_dict_cursor
from app.agents.financial_impact_agent import estimate_financial_impact


def backfill():
    conn = get_connection()
    cur = get_dict_cursor(conn)
    cur.execute("SELECT id FROM exceptions WHERE financial_impact_computed_at IS NULL ORDER BY detected_at")
    ids = [row["id"] for row in cur.fetchall()]
    cur.close()
    conn.close()

    if not ids:
        print("No exceptions need a financial impact estimate.")
        return

    priced = 0
    skipped = 0
    for i, exception_id in enumerate(ids, start=1):
        try:
            result = estimate_financial_impact(exception_id)
            if result["estimated_impact"] is not None:
                priced += 1
            else:
                skipped += 1
        except Exception as e:
            print(f"[backfill_financial_impact] Failed on {exception_id}: {e}")
            skipped += 1
        if i % 25 == 0:
            print(f"  ...{i}/{len(ids)} processed")

    print(f"\nDone. Priced {priced} exception(s), skipped {skipped} "
          f"(no linked order or no unit_cost) out of {len(ids)} total.")


if __name__ == "__main__":
    backfill()
