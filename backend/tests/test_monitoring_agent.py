"""
Tests for the deterministic severity-scoring logic in monitoring_agent.py.
No database or Ollama required — this is exactly the kind of pure,
rule-based logic that should have test coverage since the whole point of
using a formula instead of an LLM here is that it's supposed to be
predictable.
"""
import re

from app.agents.monitoring_agent import (
    compute_severity_score,
    severity_label,
    _generate_exception_id,
)


def test_severity_score_increases_with_delay():
    short = compute_severity_score(delay_days=1, quantity=100)
    long = compute_severity_score(delay_days=10, quantity=100)
    assert long > short


def test_severity_score_increases_with_quantity():
    small = compute_severity_score(delay_days=2, quantity=50)
    large = compute_severity_score(delay_days=2, quantity=2000)
    assert large > small


def test_quantity_component_is_capped():
    # quantity/500 is capped at 3.0, so a huge order shouldn't blow up the score
    huge = compute_severity_score(delay_days=0, quantity=1_000_000)
    assert huge == 3.0


def test_severity_label_boundaries():
    assert severity_label(3.0) == "Low"
    assert severity_label(3.01) == "Medium"
    assert severity_label(7.0) == "Medium"
    assert severity_label(7.01) == "High"


def test_severity_label_matches_score_for_typical_cases():
    # 5 days late, 500 units -> 5*1.2 + 1 = 7.0 -> Medium (boundary case)
    score = compute_severity_score(5, 500)
    assert score == 7.0
    assert severity_label(score) == "Medium"


def test_generated_exception_ids_are_unique_and_well_formed():
    ids = {_generate_exception_id() for _ in range(500)}
    assert len(ids) == 500  # no collisions across 500 generations
    for eid in ids:
        assert re.match(r"^EX-[0-9A-F]{8}$", eid)
