"""
Tests for app/notifications.py's pure formatting functions. The actual
network call (send_slack_notification) isn't unit tested here, same as
resolution_agent.py's _send_email isn't -- both are thin, side-effecting
wrappers around an external service; what's worth locking down with
tests is the message content they build, not the HTTP call itself.
"""
from app.notifications import (
    format_escalation_message,
    format_sla_breach_message,
    send_slack_notification,
    SLACK_WEBHOOK_URL_ENV,
)


def test_escalation_message_includes_exception_id():
    msg = format_escalation_message("EX-A1B2C3D4", "High", "Confidence too low")
    assert "EX-A1B2C3D4" in msg


def test_escalation_message_includes_reason():
    msg = format_escalation_message("EX-1", "Medium", "Needs human judgment on cost tradeoff")
    assert "Needs human judgment on cost tradeoff" in msg


def test_escalation_message_uses_severity_specific_emoji():
    high_msg = format_escalation_message("EX-1", "High", "reason")
    low_msg = format_escalation_message("EX-2", "Low", "reason")
    assert ":red_circle:" in high_msg
    assert ":large_blue_circle:" in low_msg
    assert high_msg != low_msg


def test_escalation_message_handles_unknown_severity_gracefully():
    # Shouldn't crash on an unexpected severity value -- falls back to a
    # neutral emoji rather than raising a KeyError.
    msg = format_escalation_message("EX-1", "Critical", "reason")
    assert "EX-1" in msg
    assert ":white_circle:" in msg


def test_sla_breach_message_includes_exception_id_and_severity():
    msg = format_sla_breach_message("EX-9", "High")
    assert "EX-9" in msg
    assert "High" in msg


def test_sla_breach_message_includes_hours_overdue_when_given():
    msg = format_sla_breach_message("EX-9", "High", hours_overdue=2.5)
    assert "2.5h overdue" in msg


def test_sla_breach_message_omits_hours_when_not_given():
    msg = format_sla_breach_message("EX-9", "High")
    assert "overdue)" not in msg


def test_send_slack_notification_no_ops_without_webhook_configured(monkeypatch):
    monkeypatch.delenv(SLACK_WEBHOOK_URL_ENV, raising=False)
    result = send_slack_notification("test message")
    assert result is False
