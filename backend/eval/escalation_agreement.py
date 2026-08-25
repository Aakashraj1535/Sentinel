"""
Escalation Agreement Analysis
---------------------------------
Unlike the Financial Impact evaluation, this needs NO synthetic ground
truth -- it uses REAL human judgments already captured by the app.
Every time a human reviews an escalated exception and clicks
Approve/Reject (app/main.py record_human_decision), that's a genuine
signal of whether the system's recommendation was actually correct.

What this measures: of the exceptions the system escalated to a human
(rather than auto-resolving), what fraction did the human ultimately
Approve? A high approval rate suggests escalations are well-calibrated
(the system correctly identifies cases needing human judgment, and its
recommended resolution is usually right once reviewed). A low rate
would suggest either over-escalation (flagging things that didn't need
it) or the recommended resolution itself being unreliable -- this
script can't distinguish those two causes on its own (see the printed
caveat), but it's a real, non-synthetic accuracy signal either way.

Run:  python -m eval.escalation_agreement
"""

import json
import os

from app.db import get_connection, get_dict_cursor

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")


def run():
    conn = get_connection()
    cur = get_dict_cursor(conn)

    cur.execute("""
        SELECT severity, root_cause_category, human_decision
        FROM exceptions
        WHERE human_decision IS NOT NULL
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    if not rows:
        print("No exceptions have a recorded human decision yet -- "
              "this needs at least a few Approve/Reject clicks in the app "
              "(Escalations view) before there's anything to measure.")
        return

    total = len(rows)
    approved = sum(1 for r in rows if r["human_decision"] == "Approved")
    overall_rate = round(approved / total * 100, 1)

    by_severity = {}
    for r in rows:
        bucket = by_severity.setdefault(r["severity"], {"total": 0, "approved": 0})
        bucket["total"] += 1
        if r["human_decision"] == "Approved":
            bucket["approved"] += 1
    for sev, b in by_severity.items():
        b["approval_rate_pct"] = round(b["approved"] / b["total"] * 100, 1) if b["total"] else None

    by_category = {}
    for r in rows:
        cat = r["root_cause_category"] or "Uncategorized"
        bucket = by_category.setdefault(cat, {"total": 0, "approved": 0})
        bucket["total"] += 1
        if r["human_decision"] == "Approved":
            bucket["approved"] += 1
    for cat, b in by_category.items():
        b["approval_rate_pct"] = round(b["approved"] / b["total"] * 100, 1) if b["total"] else None

    result = {
        "totalDecided": total,
        "approved": approved,
        "rejected": total - approved,
        "overallApprovalRatePct": overall_rate,
        "bySeverity": by_severity,
        "byRootCauseCategory": by_category,
        "caveat": (
            "A low approval rate could mean the system over-escalates "
            "(flags cases that didn't need human review) OR that its "
            "recommended resolution option is unreliable once a human "
            "actually checks it -- this metric alone can't separate "
            "the two causes; reading a sample of Rejected exceptions' "
            "human_decision_note is needed to tell which."
        ),
    }

    os.makedirs(RESULTS_DIR, exist_ok=True)
    out_path = os.path.join(RESULTS_DIR, "escalation_agreement.json")
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)

    print(f"Total escalated exceptions with a recorded human decision: {total}")
    print(f"Approved: {approved}  |  Rejected: {total - approved}")
    print(f"Overall approval rate: {overall_rate}%\n")

    print(f"{'Severity':<12}{'N':>6}{'Approved':>10}{'Rate (%)':>10}")
    for sev, b in by_severity.items():
        print(f"{sev:<12}{b['total']:>6}{b['approved']:>10}{b['approval_rate_pct']:>10}")

    print(f"\n{'Root cause category':<32}{'N':>6}{'Approved':>10}{'Rate (%)':>10}")
    for cat, b in by_category.items():
        print(f"{cat:<32}{b['total']:>6}{b['approved']:>10}{b['approval_rate_pct']:>10}")

    print(f"\nSaved to: {out_path}")
    print(f"\nNote: {result['caveat']}")


if __name__ == "__main__":
    run()
