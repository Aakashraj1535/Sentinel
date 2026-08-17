"""
Scheduled Executive Reporting -- generation & delivery
---------------------------------------------------------
Pulls together data that already exists elsewhere (dashboard_summary,
supplier risk levels, calibration_metrics) into one digest, and sends it
on whichever channels are configured -- reusing the exact same email/
Slack machinery already built for exception notifications. Nothing new
to configure if you already set up SCS_SMTP_EMAIL / SCS_SLACK_WEBHOOK_URL
for the SLA/escalation features; this reuses the same channels.

Runs on a schedule (see main.py, defaults to weekly), but also exposed as
a manual "send now" action via POST /api/reports/send-now for demos and
testing, so nobody has to wait a week to see what it looks like.
"""

import os

from app.db import get_connection, get_dict_cursor
from app.serializers import dashboard_summary, list_suppliers
from app.analytics import calibration_metrics
from app.agents.resolution_agent import _send_email
from app.notifications import send_slack_notification
from app.reporting import build_report_subject, build_report_text, build_report_slack_text


def generate_and_send_report() -> dict:
    """
    Builds the digest from current data and sends it on every configured
    channel. Returns a small summary dict describing what was sent --
    useful both for the manual "send now" API response and for logging.
    """
    conn = get_connection()
    cur = get_dict_cursor(conn)

    try:
        dashboard = dashboard_summary(cur)
        suppliers = list_suppliers(cur)
        calibration = calibration_metrics(cur)
    finally:
        cur.close()
        conn.close()

    at_risk_suppliers = sorted(
        [s for s in suppliers if s["riskLevel"] == "High"],
        key=lambda s: s["onTimeRate"],
    )

    subject = build_report_subject()
    email_body = build_report_text(dashboard, at_risk_suppliers, calibration)
    slack_text = build_report_slack_text(dashboard, at_risk_suppliers)

    recipient = os.environ.get("SCS_REPORT_RECIPIENT") or os.environ.get("SCS_NOTIFY_TO")
    email_sent = False
    if recipient:
        email_sent = _send_email(recipient, subject, email_body)
        if email_sent:
            print(f"[reporting] Sent executive digest email to {recipient}.")
        else:
            print(f"[reporting] Failed to send executive digest email to {recipient}.")
    else:
        print("[reporting] SCS_REPORT_RECIPIENT / SCS_NOTIFY_TO not set -- skipping email.")

    slack_sent = send_slack_notification(slack_text)
    if slack_sent:
        print("[reporting] Sent executive digest to Slack.")

    return {
        "emailSent": email_sent,
        "slackSent": slack_sent,
        "recipient": recipient,
        "atRiskSupplierCount": len(at_risk_suppliers),
        "dashboard": dashboard,
    }
