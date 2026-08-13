from app.analytics import compute_risk_level


def test_high_risk_from_low_on_time_rate():
    assert compute_risk_level(on_time_rate=80, total_incidents=0) == "High"


def test_high_risk_from_incident_count():
    assert compute_risk_level(on_time_rate=99, total_incidents=6) == "High"


def test_medium_risk():
    assert compute_risk_level(on_time_rate=90, total_incidents=1) == "Medium"
    assert compute_risk_level(on_time_rate=99, total_incidents=3) == "Medium"


def test_low_risk():
    assert compute_risk_level(on_time_rate=95, total_incidents=1) == "Low"


def test_boundaries_are_inclusive_correctly():
    # on_time_rate < 85 is High, so exactly 85 should NOT be High on its own
    assert compute_risk_level(on_time_rate=85, total_incidents=0) != "High"
    # total_incidents >= 6 is High
    assert compute_risk_level(on_time_rate=99, total_incidents=5) == "Medium"
    assert compute_risk_level(on_time_rate=99, total_incidents=6) == "High"
