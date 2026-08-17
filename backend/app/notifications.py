"""
Multi-Channel Alerting (Slack)
-------------------------------
Problem this solves: email alone means a High-severity notification can
sit unread in an inbox nobody checks in real time. Many ops/procurement
teams live in Slack, not email -- getting the alert in front of the right
person, in the tool they actually watch, is what makes human-in-the-loop
fast rather than theoretically fast.

Design choice: this ADDS a channel, it doesn't replace email. Both fire
independently on the same events (escalation, SLA breach) -- if Slack
isn't configured, this silently no-ops and email still works exactly as
before. Same "safe to leave unconfigured" philosophy as the SMTP setup
in resolution_agent.py.

Setup: create an Incoming Webhook for your Slack workspace at
https://api.slack.com/messaging/webhooks, then set:
    SCS_SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
No webhook set -> this module is a safe no-op, nothing breaks.
"""

import os
import requests

SLACK_WEBHOOK_URL_ENV = "SCS_SLACK_WEBHOOK_URL"
SLACK_TIMEOUT_SECONDS = 10

SEVERITY_EMOJI = {
    "High": ":red_circle:",
    "Medium": ":large_yellow_circle:",
    "Low": ":large_blue_circle:",
}


def _severity_emoji(severity: str) -> str:
    return SEVERITY_EMOJI.get(severity, ":white_circle:")


def format_escalation_message(exception_id: str, severity: str, escalation_reason: str) -> str:
    """Pure formatting, kept separate from the network call so it's cheap
    to unit test without mocking requests."""
    return (
        f"{_severity_emoji(severity)} *{severity} severity exception escalated* "
        f"— `{exception_id}`\n"
        f"Reason: {escalation_reason}\n"
        f"Requires human review — check the Sentinel dashboard."
    )


def format_sla_breach_message(exception_id: str, severity: str, hours_overdue: float = None) -> str:
    overdue_note = f" ({hours_overdue}h overdue)" if hours_overdue is not None else ""
    return (
        f":rotating_light: *SLA BREACHED* — `{exception_id}` "
        f"({severity} severity){overdue_note}\n"
        f"This exception is still unresolved past its response deadline. "
        f"Please review it as soon as possible."
    )


def send_slack_notification(text: str) -> bool:
    """
    Posts a message to the configured Slack webhook. Returns True on
    success, False if not configured or the send fails for any reason --
    callers should treat False as "fall back to other channels", never
    as a reason to interrupt the pipeline.
    """
    webhook_url = os.environ.get(SLACK_WEBHOOK_URL_ENV)
    if not webhook_url:
        return False  # not configured -> safe no-op, same pattern as email

    try:
        response = requests.post(
            webhook_url,
            json={"text": text},
            timeout=SLACK_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"[slack] Failed to send notification: {e}")
        return False
