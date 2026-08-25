"""
Export a sample for manual root cause labeling
----------------------------------------------------
Why this exists: unlike escalation decisions, the app doesn't currently
keep the ORIGINAL auto-assigned root cause category once a human
corrects it (see app/main.py set_root_cause_category -- it overwrites,
doesn't version), so mining existing human corrections can't give a
reliable accuracy number yet.

The standard fix in NLP/classification research when you don't have
pre-existing labels: create a small human-annotated gold-standard
sample yourself. This script exports a random sample of exceptions
(their root cause free text + the system's auto-assigned category) to
a CSV with an empty `human_label` column. Read through it, fill in what
YOU judge the correct category to be for each row (using the exact
category strings from ROOT_CAUSE_CATEGORIES, printed below), save the
file, then run eval/score_root_cause_accuracy.py on it.

This is a completely standard and expected methodology for a paper --
manual gold-standard annotation for evaluating a text classifier. Just
be honest in the paper about sample size and that one person did the
labeling (a limitation to mention, same as with the synthetic ground
truth for Financial Impact).

Run:  python -m eval.export_root_cause_sample --n 40
"""

import argparse
import csv
import os
import random

from app.db import get_connection, get_dict_cursor
from app.root_cause import ROOT_CAUSE_CATEGORIES

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")


def run(n: int):
    conn = get_connection()
    cur = get_dict_cursor(conn)
    cur.execute("""
        SELECT id, exception_type, root_cause, root_cause_category
        FROM exceptions
        WHERE root_cause IS NOT NULL AND root_cause_category IS NOT NULL
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    if not rows:
        print("No exceptions with both root_cause text and an assigned category found.")
        return

    rng = random.Random(42)
    rng.shuffle(rows)
    sample = rows[:n]

    os.makedirs(RESULTS_DIR, exist_ok=True)
    out_path = os.path.join(RESULTS_DIR, "root_cause_annotation_sample.csv")
    with open(out_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["exception_id", "exception_type", "root_cause_text",
                          "system_category", "human_label"])
        for r in sample:
            writer.writerow([r["id"], r["exception_type"], r["root_cause"],
                              r["root_cause_category"], ""])

    print(f"Exported {len(sample)} exceptions to: {out_path}")
    print(f"\nValid category labels (use EXACTLY these strings in the human_label column):")
    for c in ROOT_CAUSE_CATEGORIES:
        print(f"  - {c}")
    print(f"\nOpen the CSV, read each 'root_cause_text', and fill in 'human_label' with your "
          f"own judgment of the correct category -- WITHOUT looking at 'system_category' first "
          f"(cover it / don't peek) to avoid biasing your own labels toward the system's answer. "
          f"Once done, run:\n  python -m eval.score_root_cause_accuracy")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=40, help="Sample size to label (default 40)")
    args = parser.parse_args()
    run(args.n)
