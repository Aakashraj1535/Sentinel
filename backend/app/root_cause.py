"""
Root Cause Tagging -- classification logic
---------------------------------------------
Problem this solves: the system already captures a free-text root cause
per exception (from the LLM's resolution), but free text can't be
counted or trended -- there's no way to answer "what's our biggest
recurring problem this quarter" without someone reading every single
exception by hand. This turns that free text into a small set of
structured categories that CAN be counted, trended, and compared across
suppliers/time.

Deliberately simple keyword matching, not ML -- same philosophy as
severity scoring and SLA status: a categorization that drives supplier
conversations and contract decisions should be explainable in one
sentence, not a black box.

This is intentionally the SAME classification scheme
pattern_detection_agent.py already used for cross-supplier pattern
detection (previously defined inline there) -- extracted here so both
that feature and the new per-exception tagging/trend analytics reuse one
source of truth instead of two keyword lists silently drifting apart.
"""

# Fixed, small category set. Consistency matters more than granularity
# here -- more categories means noisier trend charts and a harder human
# override dropdown, not more insight.
ROOT_CAUSE_CATEGORIES = [
    "Port / logistics congestion",
    "Customs / documentation",
    "Supplier capacity issues",
    "Quality control",
    "Other",
]

CAUSE_KEYWORDS = {
    "Port / logistics congestion": [
        "port congestion", "highway closure", "flooding", "traffic",
        "shipping delay", "vessel", "freight delay", "transit delay",
        "weather", "storm", "road closure", "logistics",
    ],
    "Customs / documentation": [
        "customs", "documentation", "paperwork", "border", "import processing",
        "export processing", "clearance", "compliance document", "tariff",
        "inspection hold",
    ],
    "Supplier capacity issues": [
        "production line", "raw material shortage", "capacity", "backlog",
        "understaffed", "labor shortage", "overbooked", "supplier delay",
        "manufacturing delay", "factory",
    ],
    "Quality control": [
        "defect", "quality", "incorrect quantity", "damaged", "rejected batch",
        "inspection failure", "non-conforming", "spec mismatch", "wrong item",
    ],
}


def classify_root_cause(root_cause_text: str) -> str | None:
    """
    Returns a category from ROOT_CAUSE_CATEGORIES, or None if the text
    doesn't match any known keyword pattern (left for a human to tag, or
    surfaced as "Uncategorized" in aggregate views -- see analytics.py).

    Note: never returns "Other" automatically -- "Other" is reserved for
    a human explicitly saying "I looked at this and it's genuinely none
    of the above", not a keyword-matching fallback. An unmatched text
    stays None/untagged so it's visibly flagged as needing a human look,
    rather than silently buried in a catch-all bucket.
    """
    if not root_cause_text:
        return None
    text = root_cause_text.lower()
    for label, keywords in CAUSE_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return label
    return None
