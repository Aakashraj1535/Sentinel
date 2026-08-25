"""
Financial Impact estimation variants -- for the ablation study only.
------------------------------------------------------------------------
Three ways to produce the dollar figure, compared against the synthetic
ground truth (eval/generate_ground_truth.py) to answer the research
question: does grounding the LLM in a deterministic formula improve
reliability over a pure formula, or over letting the LLM guess freely?

  A. rule_based        -- production formula (app/financial_impact.py),
                           no LLM involvement at all.
  B. llm_only           -- LLM is given the same inputs and asked to
                           output a dollar figure directly, with no
                           formula to anchor it. Tests whether an LLM
                           can estimate a number "from vibes."
  C. hybrid_llm_correction -- the production formula's number (A),
                           adjusted by an LLM-suggested correction
                           multiplier clamped to [0.5, 1.5]. This is
                           NOT the production pipeline (production only
                           ever uses the LLM for the explanation text,
                           see agents/financial_impact_agent.py) -- it's
                           a research variant to test whether letting
                           the LLM nudge the number, bounded, helps or
                           hurts versus leaving the formula alone.

All three are deterministic-formula-first by design; only B has no
formula fallback, so parsing failures there fall back to a naive
15%-of-order-value guess (documented inline) rather than crashing the
evaluation run.
"""

import json
import re

import requests

from app.financial_impact import compute_financial_impact

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2"


def _call_ollama(prompt: str) -> str:
    response = requests.post(OLLAMA_URL, json={
        "model": OLLAMA_MODEL, "prompt": prompt, "stream": False,
    }, timeout=60)
    response.raise_for_status()
    return response.json()["response"].strip()


def _extract_number(text: str):
    """Pulls the first plausible dollar figure out of an LLM response.
    LLMs frequently wrap numeric answers in prose or markdown despite
    being asked for JSON only, so this is a best-effort regex fallback
    rather than a strict json.loads()."""
    match = re.search(r'-?\d[\d,]*\.?\d*', text.replace("$", ""))
    if not match:
        return None
    try:
        return float(match.group().replace(",", ""))
    except ValueError:
        return None


def variant_naive_baseline(order_value: float) -> float:
    """Naive baseline -- flat 20% of order value regardless of severity,
    SLA status, or anything else. Exists so the evaluation can show the
    rule-based formula isn't just beating AI methods, it's beating a
    trivial heuristic too."""
    return round(order_value * 0.20, 2)


def variant_rule_based(order_value: float, severity: str, sla_breached: bool) -> float:
    """Variant A -- pure formula, zero LLM calls."""
    return compute_financial_impact(order_value, severity, sla_breached)["estimatedImpact"]


def variant_llm_only(order_value: float, severity: str, sla_breached: bool,
                      exception_type: str, supplier_name: str) -> float:
    """Variant B -- LLM estimates the dollar figure directly, no formula given."""
    prompt = f"""A supply chain exception occurred. Estimate the realistic dollar financial \
impact (money at risk) of this exception. Respond with ONLY a JSON object of the form \
{{"estimated_impact": <number>}} and nothing else -- no explanation, no markdown.

Exception type: {exception_type}
Severity: {severity}
Supplier: {supplier_name}
Order value: ${order_value:,.2f}
SLA breached: {"Yes" if sla_breached else "No"}
"""
    fallback = round(order_value * 0.15, 2)  # naive guess if the LLM output can't be parsed at all
    try:
        raw = _call_ollama(prompt)
        try:
            parsed = json.loads(raw)
            value = float(parsed.get("estimated_impact"))
        except (json.JSONDecodeError, TypeError, ValueError):
            value = _extract_number(raw)
        return round(value, 2) if value is not None else fallback
    except Exception:
        return fallback


def variant_hybrid_llm_correction(order_value: float, severity: str, sla_breached: bool,
                                   exception_type: str, supplier_name: str) -> float:
    """Variant C -- research-only: formula's number (A), nudged by an
    LLM-suggested correction multiplier clamped to [0.5, 1.5] so a
    parsing failure or an extreme LLM suggestion can't blow up the
    estimate. NOT used in the production pipeline."""
    base = variant_rule_based(order_value, severity, sla_breached)
    prompt = f"""A supply chain exception's baseline estimated financial impact was calculated \
as ${base:,.2f} using a standard formula. Based on the qualitative context below, suggest a \
correction multiplier between 0.5 and 1.5 to adjust this estimate (1.0 = no change, >1.0 = \
you believe the real impact is higher, <1.0 = lower). Respond with ONLY a JSON object of the \
form {{"correction_multiplier": <number>}} and nothing else.

Exception type: {exception_type}
Severity: {severity}
Supplier: {supplier_name}
Order value: ${order_value:,.2f}
SLA breached: {"Yes" if sla_breached else "No"}
Baseline estimate: ${base:,.2f}
"""
    try:
        raw = _call_ollama(prompt)
        try:
            parsed = json.loads(raw)
            multiplier = float(parsed.get("correction_multiplier"))
        except (json.JSONDecodeError, TypeError, ValueError):
            multiplier = _extract_number(raw)
        if multiplier is None:
            multiplier = 1.0
        multiplier = max(0.5, min(1.5, multiplier))
        return round(base * multiplier, 2)
    except Exception:
        return base
