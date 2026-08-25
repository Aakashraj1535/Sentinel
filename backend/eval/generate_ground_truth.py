"""
Synthetic ground-truth generator for Financial Impact evaluation
--------------------------------------------------------------------
Methodology note (for the paper): the Financial Impact agent's
estimation formula (app/financial_impact.py) is a simple, interpretable
model: order_value x severity% (+SLA breach add-on). To evaluate it,
we need a "true" loss figure to compare against -- since no real
financial ledger exists for this synthetic dataset, we generate one
using a DELIBERATELY DIFFERENT and noisier process than the agent's own
formula. If we used the same formula to create the ground truth, the
agent would trivially score perfectly, which would be a methodologically
invalid evaluation (the model grading its own homework).

The generative process below reflects three sources of real-world
"loss" the agent's simple formula cannot see:

  1. Severity-to-loss ratio drawn from a WIDER, overlapping distribution
     per severity band, rather than the agent's fixed 5/15/35% constants
     -- real losses vary case to case even within the same severity label.
  2. A per-supplier hidden risk multiplier (~U(0.7, 1.5), seeded from the
     supplier id so it's fixed but never exposed to the agent) --
     modeling the idea that some suppliers are systematically costlier
     when things go wrong (e.g. specialty/single-source parts vs.
     commodity items), information the agent has no access to.
  3. Independent multiplicative noise (~N(1.0, 0.10)) plus an 8% chance
     the exception resolved with ~zero real financial consequence
     (caught before it mattered) -- real outcomes are noisy and
     sometimes a "High severity" flag doesn't translate into real loss.

Every exception's true_impact is generated deterministically from a
hash of its own id (not Python's global `random` seed), so re-running
this script is idempotent and reproducible without disturbing any other
script's randomness.

Run:  python -m eval.generate_ground_truth
Safe to re-run -- upserts, so parameters here can be tuned and
regenerated without needing a fresh clone of the DB.
"""

import hashlib
import json
import random

from app.db import get_connection, get_dict_cursor
from app.sla import compute_sla_status
from app.financial_impact import compute_order_value

# Wider, overlapping bands than the agent's fixed 5% / 15% / 35% constants
# (app/financial_impact.py SEVERITY_IMPACT_PCT) -- intentionally different
# so the agent's fixed constants are only approximately right.
TRUE_SEVERITY_PCT_RANGE = {
    "Low": (0.02, 0.09),
    "Medium": (0.08, 0.25),
    "High": (0.20, 0.55),
}
DEFAULT_RANGE = (0.05, 0.20)

SLA_BREACH_ADDON_RANGE = (0.05, 0.18)
ZERO_IMPACT_PROBABILITY = 0.08  # exception flagged, but no real $ consequence materialized


def _rng_for(exception_id: str) -> random.Random:
    """Deterministic per-exception RNG, seeded from a hash of the id --
    reproducible across runs without touching the global random state."""
    seed = int(hashlib.sha256(exception_id.encode()).hexdigest(), 16) % (2**32)
    return random.Random(seed)


def _supplier_risk_multiplier(supplier_id: str) -> float:
    """Fixed-per-supplier hidden risk factor, deterministic from supplier_id.
    Never computed from or exposed to the estimation agent."""
    rng = _rng_for(f"supplier-risk-{supplier_id}")
    return round(rng.uniform(0.7, 1.5), 4)


def generate_true_impact(exception_id: str, order_value: float, severity: str,
                          sla_breached: bool, supplier_id: str) -> dict:
    rng = _rng_for(exception_id)

    if rng.random() < ZERO_IMPACT_PROBABILITY:
        return {
            "trueImpact": 0.0,
            "params": {"zeroImpactCase": True, "orderValue": order_value},
        }

    low, high = TRUE_SEVERITY_PCT_RANGE.get(severity, DEFAULT_RANGE)
    true_severity_pct = rng.uniform(low, high)
    sla_addon = rng.uniform(*SLA_BREACH_ADDON_RANGE) if sla_breached else 0.0
    supplier_multiplier = _supplier_risk_multiplier(supplier_id)
    noise = max(0.5, min(1.5, rng.gauss(1.0, 0.10)))

    true_impact = round(order_value * (true_severity_pct + sla_addon) * supplier_multiplier * noise, 2)

    return {
        "trueImpact": true_impact,
        "params": {
            "zeroImpactCase": False,
            "orderValue": order_value,
            "trueSeverityPct": round(true_severity_pct, 4),
            "slaBreached": sla_breached,
            "slaAddon": round(sla_addon, 4),
            "supplierRiskMultiplier": supplier_multiplier,
            "noise": round(noise, 4),
        },
    }


def run():
    conn = get_connection()
    cur = get_dict_cursor(conn)

    cur.execute("""
        SELECT e.id, e.severity, e.status, e.detected_at, e.supplier_id, e.order_id,
               o.quantity, o.unit_cost
        FROM exceptions e
        LEFT JOIN orders o ON o.id = e.order_id
    """)
    rows = cur.fetchall()

    generated, skipped = 0, 0
    for r in rows:
        order_value = compute_order_value(r["quantity"], r["unit_cost"])
        if order_value is None:
            skipped += 1
            continue

        sla_breached = compute_sla_status(r["detected_at"], r["severity"], r["status"]) == "Breached"
        result = generate_true_impact(r["id"], order_value, r["severity"], sla_breached, r["supplier_id"])

        cur.execute("""
            INSERT INTO financial_impact_ground_truth (exception_id, true_impact, true_breakdown, generated_at)
            VALUES (%s, %s, %s, now())
            ON CONFLICT (exception_id) DO UPDATE
            SET true_impact = EXCLUDED.true_impact,
                true_breakdown = EXCLUDED.true_breakdown,
                generated_at = now()
        """, (r["id"], result["trueImpact"], json.dumps(result["params"])))
        generated += 1

    conn.commit()
    cur.close()
    conn.close()
    print(f"Ground truth generated for {generated} exception(s), skipped {skipped} (no priced order).")


if __name__ == "__main__":
    run()
