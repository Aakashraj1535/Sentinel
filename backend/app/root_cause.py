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
    # Checked AFTER supplier-capacity below (see classify_root_cause) so a
    # chronic-reliability sentence that happens to mention "logistics" or
    # "supply chain" doesn't get grabbed by this bucket first.
    "Port / logistics congestion": [
        "port congestion", "highway closure", "flooding", "traffic",
        "shipping delay", "vessel", "freight delay", "transit delay",
        "weather", "storm", "road closure",
    ],
    "Customs / documentation": [
        "customs", "documentation", "paperwork", "border", "import processing",
        "export processing", "clearance", "compliance document", "tariff",
        "inspection hold",
    ],
    # Ordered first deliberately: chronic reliability/performance language
    # ("on-time rate", "past incidents", "recurring", "history of") is a
    # stronger, more specific signal than generic logistics words, and
    # should win when both types of language appear in the same sentence.
    "Supplier capacity issues": [
        "production line", "raw material shortage", "capacity", "backlog",
        "understaffed", "labor shortage", "overbooked", "supplier delay",
        "manufacturing delay", "factory", "on-time rate", "past incidents",
        "recurring issue", "recurring delay", "history of", "chronic",
        "reliability", "track record", "systemic issue", "consistently below",
    ],
    "Quality control": [
        "defect", "quality", "incorrect quantity", "damaged", "rejected batch",
        "inspection failure", "non-conforming", "spec mismatch", "wrong item",
    ],
}

# Check order matters: supplier-capacity's more specific phrases are
# checked before the broader logistics/congestion bucket, so a sentence
# mentioning both ("no prior port congestion incidents" + "on-time rate
# below target") lands on the more specific, correct category.
_CATEGORY_CHECK_ORDER = [
    "Supplier capacity issues",
    "Quality control",
    "Customs / documentation",
    "Port / logistics congestion",
]


# Shared guidance text -- used both by resolution_agent.py's LLM prompt
# (the PRIMARY classification path) and referenced here for the keyword
# fallback's design rationale. Keeping this in one place avoids the two
# classification paths silently drifting apart on how they define each
# category, which is exactly what caused the original confusion between
# "Port / logistics congestion" and "Supplier capacity issues".
#
# v2: descriptive rules alone (v1) fixed the original under-prediction of
# "Supplier capacity issues" but overcorrected -- the model started
# pattern-matching on surface words ("supplier", "on-time rate",
# "recurring", "stockouts") regardless of whether they carried a NEGATIVE
# signal or not, misclassifying things like "on-time rate of 100.00%" as
# a reliability problem. v2 adds worked examples (few-shot) and an
# explicit "is the signal actually negative?" check, since concrete
# examples correct surface-pattern-matching far more reliably than
# abstract rules alone -- standard practice for LLM classification tasks.
CATEGORY_GUIDANCE = """Read the distinguishing guidance for each carefully -- these two are
frequently confused with each other, so pay close attention to WHICH ONE
actually fits:

- "Port / logistics congestion": a SPECIFIC, one-off transit/shipping
  event -- port congestion, a highway closure, weather, a vessel delay,
  customs holding up physical transit. The cause is something that
  happened to THIS shipment in transit.
- "Supplier capacity issues": the supplier ITSELF is the problem --
  production backlog, understaffing, raw material shortage, OR a
  pattern of chronic unreliability. IMPORTANT: only use this category if
  a NEGATIVE reliability signal is actually stated -- a low/poor
  on-time rate, an explicit count of past incidents, or a stated history
  of problems. The mere presence of the word "supplier", "on-time
  rate", "recurring", or "stockouts" is NOT enough on its own -- check
  whether the actual number or claim is negative before choosing this
  category.
- "Customs / documentation": paperwork, customs holds, compliance
  documents, import/export processing specifically.
- "Quality control": defects, wrong/incorrect quantities, damaged
  goods, failed inspections -- even when the text also mentions the
  supplier or their history, if the CORE issue described is a defect/
  wrong item/damage, this is Quality control, not Supplier capacity
  issues (a defect is a quality problem, not automatically evidence of
  chronic unreliability).
- "Other": use only if genuinely none of the above fit.

WORKED EXAMPLES (study these carefully -- they show the exact
distinctions that matter):

1. "Shipment delay caused by Meridian Logistics Co. exceeding the agreed
   delivery window of 10 business days, resulting in a high severity
   delay with no past incidents and on-time rate of 100.00%."
   -> "Port / logistics congestion". Reasoning: mentions "on-time rate"
   but the STATED VALUE is 100% (perfect) with "no past incidents" --
   that is the OPPOSITE of a reliability problem. This is a one-off
   transit delay, not a supplier pattern.

2. "Supplier on-time rate has been consistently below target, indicating
   a systemic issue with the supplier's reliability."
   -> "Supplier capacity issues". Reasoning: "consistently below
   target" is an explicit NEGATIVE reliability signal, not just the
   presence of the phrase "on-time rate".

3. "Defective shipment due to supplier quality issues or inadequate
   supplier oversight."
   -> "Quality control". Reasoning: the CORE problem is a defect
   ("defective shipment", "quality issues"). Mentioning "supplier" here
   describes WHO caused the defect, not a chronic reliability pattern --
   don't classify this as Supplier capacity issues just because the
   word "supplier" appears.

4. "Port congestion at origin port is a recurring cause of shipment
   delays for SUP-002."
   -> "Port / logistics congestion". Reasoning: "recurring" here
   describes a recurring PORT/LOGISTICS problem, not a recurring
   SUPPLIER reliability problem -- read what noun "recurring" is
   actually attached to."""


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
    for label in _CATEGORY_CHECK_ORDER:
        if any(kw in text for kw in CAUSE_KEYWORDS[label]):
            return label
    return None
