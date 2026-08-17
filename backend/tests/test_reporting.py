"""
Tests for app/reporting.py's pure formatting functions -- no database
needed, same pattern as test_notifications.py and test_sla.py.
"""
from datetime import datetime, timezone

from app.reporting import (
    build_report_subject,
    build_report_text,
    build_report_slack_text,
)

SAMPLE_DASHBOARD = {
    "activeCount": 12,
    "resolvedToday": 8,
    "escalationsPending": 3,
    "slaBreachedCount": 2,
    "slaAtRiskCount": 4,
    "avgConfidence": 78,
}

SAMPLE_SUPPLIERS = [
    {"name": "Acme Freight", "region": "North America", "onTimeRate": 62.0,
     "totalIncidents": 9, "riskLevel": "High"},
    {"name": "Meridian Logistics", "region": "APAC", "onTimeRate": 70.0,
     "totalIncidents": 6, "riskLevel": "High"},
]

SAMPLE_CALIBRATION = {"agreementRate": 84, "totalDecided": 25}


def test_subject_includes_date():
    now = datetime(2026, 3, 15, tzinfo=timezone.utc)
    subject = build_report_subject(now)
    assert "Mar 15, 2026" in subject


def test_report_text_includes_all_dashboard_figures():
    text = build_report_text(SAMPLE_DASHBOARD, [], SAMPLE_CALIBRATION)
    assert "12" in text  # active count
    assert "8" in text   # resolved
    assert "2" in text   # sla breached
    assert "4" in text   # sla at risk
    assert "78%" in text  # avg confidence


def test_report_text_lists_at_risk_suppliers():
    text = build_report_text(SAMPLE_DASHBOARD, SAMPLE_SUPPLIERS, SAMPLE_CALIBRATION)
    assert "Acme Freight" in text
    assert "Meridian Logistics" in text
    assert "High risk" in text


def test_report_text_handles_no_at_risk_suppliers_gracefully():
    text = build_report_text(SAMPLE_DASHBOARD, [], SAMPLE_CALIBRATION)
    assert "No suppliers currently at High risk" in text


def test_report_text_includes_calibration_with_sample_size():
    text = build_report_text(SAMPLE_DASHBOARD, [], SAMPLE_CALIBRATION)
    assert "84%" in text
    assert "25 human decisions" in text


def test_report_text_flags_small_sample_size():
    small_sample = {"agreementRate": 100, "totalDecided": 3}
    text = build_report_text(SAMPLE_DASHBOARD, [], small_sample)
    assert "small sample size" in text.lower()


def test_report_text_does_not_flag_large_sample_size():
    large_sample = {"agreementRate": 90, "totalDecided": 50}
    text = build_report_text(SAMPLE_DASHBOARD, [], large_sample)
    assert "small sample size" not in text.lower()


def test_report_text_handles_zero_decisions():
    empty_calibration = {"agreementRate": 0, "totalDecided": 0}
    text = build_report_text(SAMPLE_DASHBOARD, [], empty_calibration)
    assert "No human decisions recorded yet" in text


def test_slack_text_is_shorter_than_email_text():
    email_text = build_report_text(SAMPLE_DASHBOARD, SAMPLE_SUPPLIERS, SAMPLE_CALIBRATION)
    slack_text = build_report_slack_text(SAMPLE_DASHBOARD, SAMPLE_SUPPLIERS)
    assert len(slack_text) < len(email_text)


def test_slack_text_includes_top_suppliers_only():
    many_suppliers = SAMPLE_SUPPLIERS + [
        {"name": "Extra Corp", "region": "EU", "onTimeRate": 50.0,
         "totalIncidents": 12, "riskLevel": "High"},
        {"name": "Fourth Supplier", "region": "EU", "onTimeRate": 55.0,
         "totalIncidents": 10, "riskLevel": "High"},
    ]
    slack_text = build_report_slack_text(SAMPLE_DASHBOARD, many_suppliers)
    assert "Acme Freight" in slack_text
    assert "Fourth Supplier" not in slack_text  # only top 3 shown


def test_slack_text_handles_no_at_risk_suppliers():
    slack_text = build_report_slack_text(SAMPLE_DASHBOARD, [])
    assert "none" in slack_text
