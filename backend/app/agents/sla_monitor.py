"""
SLA Breach Monitor
------------------
The scheduled job that actually walks the database looking for exceptions
that have crossed into 'Breached' per app/sla.py's rules, and does
something about it: logs it to the audit trail (so it shows up in the
existing Audit Trail page with zero frontend work) and sends one
notification -- not one per scheduler tick, which would spam the same
person every few minutes for as long as the exception stays unresolved.

"Only notify once" is enforced by checking whether an 'SLA Breach' audit_log
row already exists for this exception, the same idempotency pattern
resolution_agent.py already uses for its own notifications.
"""

from app.db import get_connection, get_dict_cursor
from app.sla import compute_sla_status, hours_remaining
from app.agents.resolution_agent import _send_email, ESCALATION_ROLE_ROUTING
from app.notifications import format_sla_breach_message, send_slack_notification
import os


def _already_notified(cur, exception_id: str) -> bool:
    cur.execute("""
        SELECT 1 FROM audit_log
        WHERE exception_id = %s AND step = 'SLA Breach'
        LIMIT 1
    """, (exception_id,))
    return cur.fetchone() is not None 


def _notify_sla_breach(exception_id: str, severity: str, hours_overdue: float = None) -> str:
    role_label = ESCALATION_ROLE_ROUTING.get(severity, "ops.review.queue@company.com")
    recipient = os.environ.get("SCS_NOTIFY_TO", role_label)

    subject = f"[Sentinel] SLA BREACHED — {severity} severity exception {exception_id}"
    body = (
        f"Exception ID: {exception_id}\n"
        f"Severity: {severity}\n\n"
        f"This exception has exceeded its response SLA and is still unresolved. "
        f"Please review it as soon as possible.\n"
        f"(Sent automatically by Supply Chain Sentinel's SLA monitor.)"
    )

    sent = _send_email(recipient, subject, body)
    if sent:
        print(f"[sla] Sent SLA breach notification to {recipient} for {exception_id}.")
    else:
        print(
            f"[sla] SLA BREACH (notification not sent -- SMTP not configured): "
            f"{exception_id} ({severity})"
        )

    # Slack fires as an additional channel, independent of email -- see
    # app/notifications.py for why these aren't mutually exclusive.
    slack_text = format_sla_breach_message(exception_id, severity, hours_overdue)
    if send_slack_notification(slack_text):
        print(f"[slack] Sent SLA breach notification for {exception_id}.")

    return recipient


def check_sla_breaches() -> list:
    """
    Scans all non-terminal exceptions for SLA breaches, logs + notifies
    once per newly-breached exception. Returns the list of exception_ids
    that were newly flagged in this run (empty list if none).

    Safe to call as often as the scheduler likes -- already-flagged
    exceptions are skipped via _already_notified(), so this is idempotent.
    """
    conn = get_connection()
    cur = get_dict_cursor(conn)

    cur.execute("""
        SELECT id, severity, status, detected_at
        FROM exceptions
        WHERE status != 'Resolved'
    """)
    candidates = cur.fetchall()

    newly_breached = []
    for exc in candidates:
        status = compute_sla_status(exc["detected_at"], exc["severity"], exc["status"])
        if status != "Breached":
            continue
        if _already_notified(cur, exc["id"]):
            continue

        try:
            hours_overdue = abs(hours_remaining(exc["detected_at"], exc["severity"]))
            recipient = _notify_sla_breach(exc["id"], exc["severity"], hours_overdue)
            cur.execute("""
                INSERT INTO audit_log (exception_id, step, summary)
                VALUES (%s, 'SLA Breach', %s)
            """, (exc["id"],
                  f"SLA breached for {exc['severity']} severity exception "
                  f"({hours_overdue}h overdue). Notification sent to {recipient}."))
            conn.commit()
            newly_breached.append(exc["id"])
        except Exception as e:
            # Same principle as monitoring_agent.py: one exception's
            # notification failing shouldn't kill the rest of the sweep.
            print(f"[sla] Failed to process breach for {exc['id']}: {e}")
            conn.rollback()
            continue

    cur.close()
    conn.close()
    return newly_breached
