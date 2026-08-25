"""
Financial Impact evaluation harness
--------------------------------------
Runs all three estimation variants (eval/impact_estimation_variants.py)
against the synthetic ground truth (eval/generate_ground_truth.py) and
reports MAE, RMSE, MAPE, and Pearson correlation per variant -- the
results table for the paper's evaluation section.

Usage:
    python -m eval.run_evaluation                # default: 60-exception stratified sample
    python -m eval.run_evaluation --sample 30
    python -m eval.run_evaluation --sample 0      # 0 = evaluate every priced exception

Why sampling by default: variants B and C each make one Ollama call per
exception, so evaluating all ~285 priced exceptions means 2x285 = 570
LLM calls, which is slow on local hardware. The sample is stratified
across severity (Low/Medium/High) so small samples still cover the full
range the formula behaves differently on.

Outputs:
    eval/results/financial_impact_evaluation.csv   -- per-exception raw results
    eval/results/financial_impact_summary.json     -- per-variant metrics summary
    (also printed to stdout as a table)
"""

import argparse
import csv
import json
import math
import os
import random

from app.db import get_connection, get_dict_cursor
from app.sla import compute_sla_status
from app.financial_impact import compute_order_value
from eval.impact_estimation_variants import (
    variant_rule_based,
    variant_llm_only,
    variant_hybrid_llm_correction,
    variant_naive_baseline,
)

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
VARIANTS = ["naive_baseline", "rule_based", "llm_only", "hybrid_llm_correction"]


def _fetch_evaluable_exceptions(cur):
    cur.execute("""
        SELECT e.id, e.exception_type, e.severity, e.status, e.detected_at, e.supplier_id,
               o.quantity, o.unit_cost, s.name as supplier_name, g.true_impact
        FROM exceptions e
        JOIN financial_impact_ground_truth g ON g.exception_id = e.id
        LEFT JOIN orders o ON o.id = e.order_id
        LEFT JOIN suppliers s ON s.id = e.supplier_id
    """)
    return cur.fetchall()


def _stratified_sample(rows, n):
    if n <= 0 or n >= len(rows):
        return rows
    by_severity = {}
    for r in rows:
        by_severity.setdefault(r["severity"], []).append(r)
    per_bucket = max(1, n // max(1, len(by_severity)))
    rng = random.Random(42)
    sample = []
    for bucket_rows in by_severity.values():
        rng.shuffle(bucket_rows)
        sample.extend(bucket_rows[:per_bucket])
    return sample[:n]


def _wilcoxon_signed_rank(a, b):
    """
    Paired Wilcoxon signed-rank test (two-tailed, normal approximation),
    implemented without scipy since it isn't a project dependency. Used
    to test whether one variant's absolute errors are significantly
    different from another's, rather than relying on eyeballing whether
    two MAE numbers "look close."

    Normal approximation is standard practice once n is reasonably large
    (our sample sizes are 60-285, well within where this approximation
    is considered reliable) -- see Wilcoxon (1945) / standard nonparametric
    stats references. Zero differences are dropped before ranking, per
    the standard procedure.

    Returns (z_statistic, two_tailed_p_value).
    """
    diffs = [x - y for x, y in zip(a, b) if x != y]
    n = len(diffs)
    if n == 0:
        return 0.0, 1.0

    abs_diffs = sorted(range(n), key=lambda i: abs(diffs[i]))
    ranks = [0.0] * n
    i = 0
    rank = 1
    while i < n:
        j = i
        while j + 1 < n and abs(diffs[abs_diffs[j + 1]]) == abs(diffs[abs_diffs[i]]):
            j += 1
        avg_rank = (rank + rank + (j - i)) / 2
        for k in range(i, j + 1):
            ranks[abs_diffs[k]] = avg_rank
        rank += (j - i + 1)
        i = j + 1

    w_pos = sum(ranks[i] for i in range(n) if diffs[i] > 0)
    mean_w = n * (n + 1) / 4
    std_w = math.sqrt(n * (n + 1) * (2 * n + 1) / 24)
    if std_w == 0:
        return 0.0, 1.0
    z = (w_pos - mean_w) / std_w
    p = 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))
    return round(z, 4), round(p, 6)


def _metrics(true_vals, pred_vals):
    n = len(true_vals)
    if n == 0:
        return {"n": 0, "mae": None, "rmse": None, "mape": None, "pearson_r": None}

    errors = [p - t for p, t in zip(pred_vals, true_vals)]
    abs_errors = [abs(e) for e in errors]
    mae = sum(abs_errors) / n
    rmse = math.sqrt(sum(e ** 2 for e in errors) / n)

    # MAPE only over cases with nonzero true impact -- undefined otherwise
    nonzero = [(t, p) for t, p in zip(true_vals, pred_vals) if t != 0]
    mape = (sum(abs((p - t) / t) for t, p in nonzero) / len(nonzero) * 100) if nonzero else None

    mean_t = sum(true_vals) / n
    mean_p = sum(pred_vals) / n
    cov = sum((t - mean_t) * (p - mean_p) for t, p in zip(true_vals, pred_vals))
    var_t = sum((t - mean_t) ** 2 for t in true_vals)
    var_p = sum((p - mean_p) ** 2 for p in pred_vals)
    pearson_r = cov / math.sqrt(var_t * var_p) if var_t > 0 and var_p > 0 else None

    return {
        "n": n,
        "mae": round(mae, 2),
        "rmse": round(rmse, 2),
        "mape": round(mape, 2) if mape is not None else None,
        "pearson_r": round(pearson_r, 4) if pearson_r is not None else None,
    }


def run(sample_size: int):
    conn = get_connection()
    cur = get_dict_cursor(conn)
    rows = _fetch_evaluable_exceptions(cur)
    cur.close()
    conn.close()

    evaluable = [r for r in rows if compute_order_value(r["quantity"], r["unit_cost"]) is not None]
    skipped_unpriced = len(rows) - len(evaluable)
    sample = _stratified_sample(evaluable, sample_size)

    print(f"Evaluating {len(sample)} of {len(evaluable)} priced exceptions with ground truth "
          f"({skipped_unpriced} skipped, no priced order)...\n")

    os.makedirs(RESULTS_DIR, exist_ok=True)
    per_exception_rows = []
    predictions = {v: [] for v in VARIANTS}
    true_vals = []

    for i, r in enumerate(sample, start=1):
        order_value = compute_order_value(r["quantity"], r["unit_cost"])
        sla_breached = compute_sla_status(r["detected_at"], r["severity"], r["status"]) == "Breached"
        supplier_name = r["supplier_name"] or r["supplier_id"]

        pred_naive = variant_naive_baseline(order_value)
        pred_a = variant_rule_based(order_value, r["severity"], sla_breached)
        pred_b = variant_llm_only(order_value, r["severity"], sla_breached, r["exception_type"], supplier_name)
        pred_c = variant_hybrid_llm_correction(order_value, r["severity"], sla_breached, r["exception_type"], supplier_name)

        true_impact = float(r["true_impact"])
        true_vals.append(true_impact)
        predictions["naive_baseline"].append(pred_naive)
        predictions["rule_based"].append(pred_a)
        predictions["llm_only"].append(pred_b)
        predictions["hybrid_llm_correction"].append(pred_c)

        per_exception_rows.append({
            "exception_id": r["id"], "severity": r["severity"], "order_value": order_value,
            "sla_breached": sla_breached, "true_impact": true_impact,
            "naive_baseline": pred_naive,
            "rule_based": pred_a, "llm_only": pred_b, "hybrid_llm_correction": pred_c,
        })

        if i % 10 == 0:
            print(f"  ...{i}/{len(sample)} evaluated")

    csv_path = os.path.join(RESULTS_DIR, "financial_impact_evaluation.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(per_exception_rows[0].keys()))
        writer.writeheader()
        writer.writerows(per_exception_rows)

    summary = {variant: _metrics(true_vals, predictions[variant]) for variant in VARIANTS}

    # Significance: is rule_based's absolute error meaningfully different
    # from each other variant's, or could the gap be noise? Compares
    # PAIRED absolute errors per exception (not the raw estimates), since
    # that's what we actually care about being different.
    rule_errors = [abs(p - t) for p, t in zip(predictions["rule_based"], true_vals)]
    significance = {}
    for variant in VARIANTS:
        if variant == "rule_based":
            continue
        other_errors = [abs(p - t) for p, t in zip(predictions[variant], true_vals)]
        z, p_value = _wilcoxon_signed_rank(rule_errors, other_errors)
        significance[f"rule_based_vs_{variant}"] = {
            "z": z, "p_value": p_value, "significant_at_0.05": p_value < 0.05,
        }

    summary_path = os.path.join(RESULTS_DIR, "financial_impact_summary.json")
    with open(summary_path, "w") as f:
        json.dump({"metrics": summary, "significance": significance}, f, indent=2)

    print(f"\n{'Variant':<24}{'N':>5}{'MAE (Rs.)':>12}{'RMSE (Rs.)':>12}{'MAPE (%)':>12}{'Pearson r':>12}")
    print("-" * 77)
    for variant, m in summary.items():
        print(f"{variant:<24}{m['n']:>5}{m['mae']:>12}{m['rmse']:>12}"
              f"{m['mape'] if m['mape'] is not None else '-':>12}"
              f"{m['pearson_r'] if m['pearson_r'] is not None else '-':>12}")

    print(f"\nSignificance (rule_based's error vs. each variant's error, Wilcoxon signed-rank):")
    for label, s in significance.items():
        sig_note = "SIGNIFICANT (p<0.05)" if s["significant_at_0.05"] else "not significant"
        print(f"  {label:<38} z={s['z']:>8}  p={s['p_value']:>10}  {sig_note}")

    print(f"\nRaw per-exception results: {csv_path}")
    print(f"Summary metrics + significance: {summary_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=int, default=60,
                         help="Number of exceptions to evaluate (0 = all). Default 60, stratified by severity.")
    args = parser.parse_args()
    run(args.sample)
