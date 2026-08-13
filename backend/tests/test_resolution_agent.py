"""
Tests for the grounding-score / confidence-blending logic in
resolution_agent.py. This is the fix for the LLM's self-reported confidence
staying artificially high regardless of retrieved context (documented in
eval_harness/run_eval.py) — worth locking down with tests since a
regression here would silently bring back the overconfidence bug.
"""
from app.agents.resolution_agent import (
    compute_grounding_score,
    blend_confidence,
    confidence_label,
)


def test_grounding_score_with_no_context_is_low():
    assert compute_grounding_score([]) == 10.0


def test_grounding_score_rewards_supplier_linked_docs():
    supplier_linked = [{"relevance": "supplier-linked", "distance": 0.2}]
    similarity_only = [{"relevance": "similarity", "distance": 0.2}]
    assert compute_grounding_score(supplier_linked) > compute_grounding_score(similarity_only)


def test_grounding_score_rewards_more_corroborating_docs():
    one_doc = [{"relevance": "type-linked", "distance": 0.5}]
    five_docs = [{"relevance": "type-linked", "distance": 0.5}] * 5
    assert compute_grounding_score(five_docs) > compute_grounding_score(one_doc)


def test_grounding_score_is_capped_at_100():
    strong_docs = [{"relevance": "supplier-linked", "distance": 0.0}] * 5
    assert compute_grounding_score(strong_docs) <= 100.0


def test_blend_confidence_pulls_down_high_llm_confidence_with_no_grounding():
    # This is the actual bug being fixed: LLM says 85% confident even when
    # nothing relevant was retrieved. Blending should meaningfully lower it.
    raw_llm_confidence = 85.0
    grounding_score = compute_grounding_score([])  # no context retrieved
    blended = blend_confidence(raw_llm_confidence, grounding_score)
    assert blended < raw_llm_confidence


def test_blend_confidence_stays_high_with_strong_grounding():
    raw_llm_confidence = 85.0
    grounding_score = compute_grounding_score(
        [{"relevance": "supplier-linked", "distance": 0.1}] * 3
    )
    blended = blend_confidence(raw_llm_confidence, grounding_score)
    assert blended >= 70  # still high when context genuinely supports it


def test_blend_confidence_bounds():
    assert blend_confidence(0, 0) == 0
    assert blend_confidence(100, 100) == 100


def test_confidence_label_thresholds():
    assert confidence_label(74.9) == "Medium"
    assert confidence_label(75) == "High"
    assert confidence_label(50) == "Medium"
    assert confidence_label(49.9) == "Low"
