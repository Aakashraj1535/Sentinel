"""
Score root cause classification accuracy against manual labels
---------------------------------------------------------------------
Reads back the CSV produced by eval/export_root_cause_sample.py (after
you've filled in the human_label column) and computes overall accuracy
plus per-category precision/recall/F1 -- the standard metrics for a
multi-class text classifier, comparing the system's auto-assigned
category (root_cause.py's keyword matching / the LLM's chosen category)
against your own manual judgment.

Run:  python -m eval.score_root_cause_accuracy
"""

import csv
import json
import os

from app.root_cause import ROOT_CAUSE_CATEGORIES

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
INPUT_PATH = os.path.join(RESULTS_DIR, "root_cause_annotation_sample.csv")


def run():
    if not os.path.exists(INPUT_PATH):
        print(f"No annotation file found at {INPUT_PATH}.")
        print("Run 'python -m eval.export_root_cause_sample' first, label it, then re-run this.")
        return

    with open(INPUT_PATH, newline="") as f:
        rows = list(csv.DictReader(f))

    unlabeled = [r for r in rows if not r["human_label"].strip()]
    if unlabeled:
        print(f"{len(unlabeled)} of {len(rows)} row(s) still have an empty human_label -- "
              f"fill those in before scoring (currently scoring only the {len(rows) - len(unlabeled)} labeled rows).")

    labeled = [r for r in rows if r["human_label"].strip()]
    if not labeled:
        print("No labeled rows to score yet.")
        return

    bad_labels = [r for r in labeled if r["human_label"] not in ROOT_CAUSE_CATEGORIES]
    if bad_labels:
        print(f"WARNING: {len(bad_labels)} row(s) have a human_label that doesn't exactly match "
              f"one of ROOT_CAUSE_CATEGORIES -- these will be excluded. Check for typos:")
        for r in bad_labels[:5]:
            print(f"  {r['exception_id']}: {r['human_label']!r}")
        labeled = [r for r in labeled if r["human_label"] in ROOT_CAUSE_CATEGORIES]

    n = len(labeled)
    correct = sum(1 for r in labeled if r["system_category"] == r["human_label"])
    accuracy = round(correct / n * 100, 1) if n else None

    # Per-category precision / recall / F1
    per_category = {}
    for cat in ROOT_CAUSE_CATEGORIES:
        tp = sum(1 for r in labeled if r["system_category"] == cat and r["human_label"] == cat)
        fp = sum(1 for r in labeled if r["system_category"] == cat and r["human_label"] != cat)
        fn = sum(1 for r in labeled if r["system_category"] != cat and r["human_label"] == cat)
        precision = round(tp / (tp + fp), 3) if (tp + fp) else None
        recall = round(tp / (tp + fn), 3) if (tp + fn) else None
        f1 = round(2 * precision * recall / (precision + recall), 3) if precision and recall and (precision + recall) else None
        per_category[cat] = {"tp": tp, "fp": fp, "fn": fn, "precision": precision, "recall": recall, "f1": f1}

    result = {"n": n, "correct": correct, "accuracy_pct": accuracy, "perCategory": per_category}
    out_path = os.path.join(RESULTS_DIR, "root_cause_accuracy.json")
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)

    print(f"\nScored {n} manually labeled exception(s).")
    print(f"Overall accuracy: {accuracy}% ({correct}/{n} matched your label)\n")
    print(f"{'Category':<32}{'TP':>5}{'FP':>5}{'FN':>5}{'Precision':>12}{'Recall':>10}{'F1':>8}")
    for cat, m in per_category.items():
        print(f"{cat:<32}{m['tp']:>5}{m['fp']:>5}{m['fn']:>5}"
              f"{m['precision'] if m['precision'] is not None else '-':>12}"
              f"{m['recall'] if m['recall'] is not None else '-':>10}"
              f"{m['f1'] if m['f1'] is not None else '-':>8}")
    print(f"\nSaved to: {out_path}")


if __name__ == "__main__":
    run()
