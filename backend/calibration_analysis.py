"""
Calibration analysis for Supply Chain Sentinel's Resolution Agent.
-------------------------------------------------------------------
Computes two standard calibration metrics on your eval_harness results,
and sweeps the LLM/grounding blend ratio to find the value that
minimizes calibration error -- turning the qualitative "confidence
stayed flat" finding into quantitative, citable numbers.

METRICS:
- Expected Calibration Error (ECE): bins predictions by confidence,
  measures the average gap between stated confidence and actual
  accuracy within each bin. Lower is better. 0 = perfectly calibrated.
- Brier Score: mean squared error between confidence (as a probability)
  and the binary outcome. Lower is better. 0 = perfect, 0.25 = the score
  you'd get by always guessing 50%.

"Outcome" here = whether the system's escalation decision matched your
recorded human judgment (system_agrees_with_human) -- i.e. we treat
"confidence" as the model's confidence that its decision was correct,
and "outcome" as whether it actually was.

Requires results.csv to have been generated AFTER the raw_llm_confidence_pct
/ grounding_score columns were added (i.e. after applying
migrate_add_calibration_columns.py + the updated resolution_agent.py, and
re-running eval_harness/run_eval.py at least once).

Run:
    python3 calibration_analysis.py
"""
import csv
from pathlib import Path

RESULTS_PATH = Path("eval_harness/results.csv")
N_BINS = 5  # small dataset (20 scenarios) -> fewer bins than the usual 10


def load_rows():
    rows = []
    with open(RESULTS_PATH, newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            if not r.get("confidence_pct"):
                continue
            rows.append(r)
    return rows


def to_float(v, default=None):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def compute_ece_and_brier(confidences: list[float], outcomes: list[int], n_bins=N_BINS):
    """
    confidences: list of 0-1 confidence values
    outcomes: list of 0/1 (1 = system agreed with human judgment)
    """
    n = len(confidences)
    if n == 0:
        return None, None

    brier = sum((c - o) ** 2 for c, o in zip(confidences, outcomes)) / n

    bin_edges = [i / n_bins for i in range(n_bins + 1)]
    ece = 0.0
    bin_report = []
    for i in range(n_bins):
        lo, hi = bin_edges[i], bin_edges[i + 1]
        in_bin = [(c, o) for c, o in zip(confidences, outcomes) if lo <= c < hi or (i == n_bins - 1 and c == hi)]
        if not in_bin:
            continue
        bin_conf = sum(c for c, _ in in_bin) / len(in_bin)
        bin_acc = sum(o for _, o in in_bin) / len(in_bin)
        weight = len(in_bin) / n
        ece += weight * abs(bin_conf - bin_acc)
        bin_report.append((f"{lo:.1f}-{hi:.1f}", len(in_bin), round(bin_conf, 3), round(bin_acc, 3)))

    return round(ece, 4), round(brier, 4), bin_report


def blend(raw_llm, grounding, llm_weight):
    return (llm_weight * raw_llm) + ((1 - llm_weight) * grounding)


def main():
    if not RESULTS_PATH.exists():
        print(f"ERROR: {RESULTS_PATH} not found. Run eval_harness/run_eval.py first.")
        return

    rows = load_rows()
    outcomes = [1 if r["system_agrees_with_human"] == "True" else 0 for r in rows]

    # --- 1. Calibration of the CURRENT (already-blended, 0.6/0.4) confidence ---
    current_conf = [to_float(r["confidence_pct"]) / 100 for r in rows]
    ece, brier, bins = compute_ece_and_brier(current_conf, outcomes)

    print("=" * 70)
    print("CURRENT SYSTEM (60% LLM / 40% grounding blend)")
    print("=" * 70)
    print(f"  Expected Calibration Error (ECE): {ece}")
    print(f"  Brier Score:                      {brier}")
    print(f"  {'Bin':<10}{'N':<5}{'Avg Conf':<12}{'Accuracy':<10}")
    for b in bins:
        print(f"  {b[0]:<10}{b[1]:<5}{b[2]:<12}{b[3]:<10}")

    # --- 2. Calibration if using RAW LLM confidence only (no grounding fix) ---
    raw_available = [r for r in rows if r.get("raw_llm_confidence_pct")]
    if raw_available:
        raw_conf = [to_float(r["raw_llm_confidence_pct"]) / 100 for r in raw_available]
        raw_outcomes = [1 if r["system_agrees_with_human"] == "True" else 0 for r in raw_available]
        raw_ece, raw_brier, _ = compute_ece_and_brier(raw_conf, raw_outcomes)
        print()
        print("=" * 70)
        print("BASELINE: RAW LLM CONFIDENCE ONLY (pre-fix, for comparison)")
        print("=" * 70)
        print(f"  Expected Calibration Error (ECE): {raw_ece}")
        print(f"  Brier Score:                      {raw_brier}")
        print(f"  -> Grounding fix changed ECE by {round(raw_ece - ece, 4)} "
              f"({'improvement' if ece < raw_ece else 'regression'})")

        # --- 3. Ablation: sweep the blend ratio ---
        print()
        print("=" * 70)
        print("ABLATION: sweeping LLM/grounding blend ratio")
        print("=" * 70)
        print(f"  {'LLM weight':<12}{'Grounding weight':<18}{'ECE':<10}{'Brier':<10}")
        best = None
        for llm_w_pct in range(0, 101, 10):
            llm_w = llm_w_pct / 100
            blended = []
            for r in raw_available:
                raw = to_float(r["raw_llm_confidence_pct"])
                ground = to_float(r["grounding_score"])
                if raw is None or ground is None:
                    continue
                blended.append(blend(raw, ground, llm_w) / 100)
            if not blended:
                continue
            sweep_ece, sweep_brier, _ = compute_ece_and_brier(blended, raw_outcomes)
            print(f"  {llm_w:<12}{round(1 - llm_w, 2):<18}{sweep_ece:<10}{sweep_brier:<10}")
            if best is None or sweep_ece < best[1]:
                best = (llm_w, sweep_ece, sweep_brier)

        print()
        print(f"  Best blend found: {best[0]*100:.0f}% LLM / {(1-best[0])*100:.0f}% grounding "
              f"(ECE={best[1]}, Brier={best[2]})")
        print(f"  Current hardcoded blend is 60% LLM / 40% grounding.")
    else:
        print()
        print("NOTE: raw_llm_confidence_pct / grounding_score not found in results.csv.")
        print("Run migrate_add_calibration_columns.py, update resolution_agent.py,")
        print("then re-run eval_harness/run_eval.py to populate these columns.")


if __name__ == "__main__":
    main()
