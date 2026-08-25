"""
Before/After: root cause classification fix
------------------------------------------------
Uses the SAME human labels you already collected (root_cause_
annotation_sample.csv) to measure whether the prompt/keyword fix in
app/root_cause.py and agents/resolution_agent.py actually improved
accuracy -- without needing to relabel anything.

"Before" = the system_category column already in your CSV (the
original, pre-fix classification).
"After" = re-classifies the SAME root_cause_text using the NEW
improved prompt (a focused, category-only Ollama call -- not the full
resolution prompt, so this is cheap and fast) and scores that against
your same human_label column.

This does NOT touch your database -- it's a read-only comparison, safe
to run without disturbing any exception's stored root_cause_category.

Run:  python -m eval.compare_root_cause_fix
"""

import csv
import json
import os

import requests

from app.root_cause import ROOT_CAUSE_CATEGORIES, CATEGORY_GUIDANCE, classify_root_cause

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2"

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
SAMPLE_PATH = os.path.join(RESULTS_DIR, "root_cause_annotation_sample.csv")
BEFORE_AFTER_PATH = os.path.join(RESULTS_DIR, "root_cause_before_after.csv")


def _reclassify(root_cause_text: str) -> str:
    """Focused, category-only re-classification using the improved
    guidance -- cheaper than the full resolution prompt since it's just
    asking for a category, not resolution options too."""
    prompt = f"""Classify the root cause of a supply chain exception into EXACTLY ONE of \
these fixed categories.
{CATEGORY_GUIDANCE}

Root cause: {root_cause_text}

Before choosing, briefly reason about which category fits (1 short
sentence) -- specifically check whether any reliability claim you're
about to rely on is actually negative, not just present.

Respond with ONLY valid JSON: {{"category_reasoning": "1 short sentence", "category": "one of the fixed categories above, exactly as written"}}
"""
    try:
        response = requests.post(OLLAMA_URL, json={
            "model": OLLAMA_MODEL, "prompt": prompt, "stream": False,
        }, timeout=60)
        response.raise_for_status()
        raw = response.json()["response"].strip()
        raw = raw.strip("`").replace("json\n", "").strip()
        parsed = json.loads(raw)
        category = parsed.get("category")
        if category in ROOT_CAUSE_CATEGORIES:
            return category
    except Exception:
        pass
    # Fall back to the (also-improved) keyword matcher if the LLM call
    # fails or returns something unparseable -- same fallback the
    # production pipeline uses.
    return classify_root_cause(root_cause_text) or "Other"


def _accuracy(rows, category_key):
    n = len(rows)
    correct = sum(1 for r in rows if r[category_key] == r["human_label"])
    return round(correct / n * 100, 1) if n else None, correct, n


def run():
    # Prefer the 3-way file (original -> v1 fix) if it exists from a
    # previous run, so this run adds a v2 column on top rather than
    # losing the v1 comparison. Falls back to the original export if
    # this is the first time running any comparison.
    three_way = os.path.exists(BEFORE_AFTER_PATH)
    source_path = BEFORE_AFTER_PATH if three_way else SAMPLE_PATH

    if not os.path.exists(source_path):
        print(f"No annotation file found. Run eval/export_root_cause_sample.py first.")
        return

    with open(source_path, newline="") as f:
        raw_rows = list(csv.DictReader(f))

    if three_way:
        rows = [r for r in raw_rows if r["human_label"].strip() in ROOT_CAUSE_CATEGORIES]
        original_key, v1_key = "before", "after"
    else:
        rows = [r for r in raw_rows if r["human_label"].strip() in ROOT_CAUSE_CATEGORIES]
        original_key, v1_key = "system_category", None

    if not rows:
        print("No fully labeled rows found -- make sure root_cause_annotation_sample.csv is complete.")
        return

    print(f"Re-classifying {len(rows)} exceptions with the v2 (few-shot) prompt...\n")
    for i, r in enumerate(rows, start=1):
        r["v2_category"] = _reclassify(r["root_cause_text"])
        if i % 10 == 0:
            print(f"  ...{i}/{len(rows)} reclassified")

    original_acc, original_correct, n = _accuracy(rows, original_key)
    v2_acc, v2_correct, _ = _accuracy(rows, "v2_category")
    if v1_key:
        v1_acc, v1_correct, _ = _accuracy(rows, v1_key)

    changed = [r for r in rows if r[original_key] != r["v2_category"]]
    improved = [r for r in changed if r["v2_category"] == r["human_label"] and r[original_key] != r["human_label"]]
    worsened = [r for r in changed if r[original_key] == r["human_label"] and r["v2_category"] != r["human_label"]]

    out_path = os.path.join(RESULTS_DIR, "root_cause_before_after.csv")
    with open(out_path, "w", newline="") as f:
        fieldnames = ["exception_id", "root_cause_text", "human_label", "before"]
        if v1_key:
            fieldnames.append("v1_after")
        fieldnames.append("after")  # "after" always holds the LATEST version, for chaining future runs
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            row_out = {
                "exception_id": r["exception_id"], "root_cause_text": r["root_cause_text"],
                "human_label": r["human_label"], "before": r[original_key], "after": r["v2_category"],
            }
            if v1_key:
                row_out["v1_after"] = r[v1_key]
            writer.writerow(row_out)

    print(f"\n{'='*60}")
    print(f"ORIGINAL (no fix):              {original_acc}%  ({original_correct}/{n})")
    if v1_key:
        print(f"V1 FIX (rules only):            {v1_acc}%  ({v1_correct}/{n})")
    print(f"V2 FIX (rules + few-shot + CoT): {v2_acc}%  ({v2_correct}/{n})")
    print(f"{'='*60}")
    print(f"\n{len(changed)} classification(s) changed vs. original.")
    print(f"  Improved (was wrong, now right): {len(improved)}")
    print(f"  Worsened (was right, now wrong): {len(worsened)}")
    print(f"\nFull comparison saved to: {out_path}")


if __name__ == "__main__":
    run()
