"""
Supplier Scorecards Over Time -- trend direction logic
---------------------------------------------------------
Problem this solves: supplier performance elsewhere in this app (the
suppliers list, risk badges) is a SNAPSHOT -- today's on-time rate and
incident count. Two suppliers can show the identical 90% on-time rate
today while one has been steady at 90% for a year and the other just
fell from 98% last month. Those are very different risk profiles, and a
snapshot can't tell them apart. This is the "is it getting better or
worse" answer a snapshot can't give.

Kept as pure, testable logic separate from the DB query that builds the
weekly series (see analytics.py's supplier_weekly_trend) -- same
separation pattern as sla.py/sla_monitor.py and root_cause.py/
resolution_agent.py elsewhere in this codebase.
"""

# Minimum number of delivered orders required in EACH comparison window
# before trusting a trend verdict. Below this, a single early/late
# delivery can swing the rate wildly -- "Insufficient data" is a more
# honest answer than a confident-looking verdict built on 2 orders.
MIN_ORDERS_PER_WINDOW = 3

# A rate change smaller than this is noise, not a real trend -- avoids
# flip-flopping between "Improving" and "Declining" over a 1-2 point
# wobble that doesn't mean anything operationally.
STABLE_THRESHOLD_POINTS = 5.0


def compute_trend_direction(
    recent_on_time_rate: float,
    recent_order_count: int,
    prior_on_time_rate: float,
    prior_order_count: int,
) -> str:
    """
    Compares a recent window's on-time rate against the prior window of
    the same length. Returns 'Improving', 'Declining', 'Stable', or
    'Insufficient data'.
    """
    if recent_order_count < MIN_ORDERS_PER_WINDOW or prior_order_count < MIN_ORDERS_PER_WINDOW:
        return "Insufficient data"

    delta = recent_on_time_rate - prior_on_time_rate
    if delta >= STABLE_THRESHOLD_POINTS:
        return "Improving"
    if delta <= -STABLE_THRESHOLD_POINTS:
        return "Declining"
    return "Stable"
