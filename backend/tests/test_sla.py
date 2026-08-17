"""
Tests for app/sla.py -- pure logic, no database needed. This is exactly
the kind of deterministic rule that's cheap to test and easy to silently
break (e.g. an off-by-one in the At Risk threshold going unnoticed).
"""
from datetime import datetime, timedelta, timezone

from app.sla import (
    sla_hours_for_severity,
    compute_sla_deadline,
    compute_sla_status,
    hours_remaining,
)


def test_sla_hours_by_severity():
    assert sla_hours_for_severity("High") == 4
    assert sla_hours_for_severity("Medium") == 24
    assert sla_hours_for_severity("Low") == 72


def test_unknown_severity_falls_back_to_most_generous_window():
    assert sla_hours_for_severity("Unknown") == sla_hours_for_severity("Low")


def test_compute_sla_deadline():
    detected = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    deadline = compute_sla_deadline(detected, "High")
    assert deadline == detected + timedelta(hours=4)


def test_resolved_exception_is_always_complete_regardless_of_time():
    detected = datetime(2020, 1, 1, tzinfo=timezone.utc)  # ancient, would be breached
    status = compute_sla_status(detected, "High", "Resolved")
    assert status == "Complete"


def test_on_track_just_after_detection():
    now = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    detected = now  # just detected
    status = compute_sla_status(detected, "High", "Active", now=now)
    assert status == "On Track"


def test_at_risk_past_75_percent_of_window():
    detected = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    # High = 4h window, 75% = 3h in
    now = detected + timedelta(hours=3, minutes=1)
    status = compute_sla_status(detected, "High", "Active", now=now)
    assert status == "At Risk"


def test_still_on_track_just_before_75_percent():
    detected = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    now = detected + timedelta(hours=2, minutes=59)
    status = compute_sla_status(detected, "High", "Active", now=now)
    assert status == "On Track"


def test_breached_past_full_window():
    detected = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    now = detected + timedelta(hours=4, minutes=1)
    status = compute_sla_status(detected, "High", "Active", now=now)
    assert status == "Breached"


def test_escalated_status_is_still_sla_tracked_not_complete():
    # Rejecting a recommendation doesn't mean the SLA clock stops --
    # the underlying problem is still open.
    detected = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    now = detected + timedelta(hours=5)
    status = compute_sla_status(detected, "High", "Escalated", now=now)
    assert status == "Breached"


def test_low_severity_has_much_longer_runway_than_high():
    detected = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    now = detected + timedelta(hours=5)  # would breach High, not Low
    high_status = compute_sla_status(detected, "High", "Active", now=now)
    low_status = compute_sla_status(detected, "Low", "Active", now=now)
    assert high_status == "Breached"
    assert low_status == "On Track"


def test_hours_remaining_positive_before_deadline():
    detected = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    now = detected + timedelta(hours=1)
    remaining = hours_remaining(detected, "High", now=now)
    assert remaining == 3.0


def test_hours_remaining_negative_after_breach():
    detected = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    now = detected + timedelta(hours=6)
    remaining = hours_remaining(detected, "High", now=now)
    assert remaining == -2.0
