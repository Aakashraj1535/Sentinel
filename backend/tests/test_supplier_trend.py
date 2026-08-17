from app.supplier_trend import compute_trend_direction, MIN_ORDERS_PER_WINDOW


def test_improving_when_recent_rate_much_higher():
    result = compute_trend_direction(
        recent_on_time_rate=95.0, recent_order_count=10,
        prior_on_time_rate=80.0, prior_order_count=10,
    )
    assert result == "Improving"


def test_declining_when_recent_rate_much_lower():
    result = compute_trend_direction(
        recent_on_time_rate=70.0, recent_order_count=10,
        prior_on_time_rate=95.0, prior_order_count=10,
    )
    assert result == "Declining"


def test_stable_when_small_change():
    result = compute_trend_direction(
        recent_on_time_rate=91.0, recent_order_count=10,
        prior_on_time_rate=90.0, prior_order_count=10,
    )
    assert result == "Stable"


def test_exactly_at_threshold_counts_as_moved():
    result = compute_trend_direction(
        recent_on_time_rate=95.0, recent_order_count=10,
        prior_on_time_rate=90.0, prior_order_count=10,
    )
    assert result == "Improving"


def test_insufficient_data_when_recent_window_too_small():
    result = compute_trend_direction(
        recent_on_time_rate=100.0, recent_order_count=1,
        prior_on_time_rate=50.0, prior_order_count=10,
    )
    assert result == "Insufficient data"


def test_insufficient_data_when_prior_window_too_small():
    result = compute_trend_direction(
        recent_on_time_rate=100.0, recent_order_count=10,
        prior_on_time_rate=50.0, prior_order_count=1,
    )
    assert result == "Insufficient data"


def test_insufficient_data_when_both_windows_empty():
    result = compute_trend_direction(
        recent_on_time_rate=0, recent_order_count=0,
        prior_on_time_rate=0, prior_order_count=0,
    )
    assert result == "Insufficient data"


def test_boundary_exactly_at_min_orders_is_sufficient():
    result = compute_trend_direction(
        recent_on_time_rate=100.0, recent_order_count=MIN_ORDERS_PER_WINDOW,
        prior_on_time_rate=100.0, prior_order_count=MIN_ORDERS_PER_WINDOW,
    )
    assert result != "Insufficient data"


def test_one_below_min_orders_is_insufficient():
    result = compute_trend_direction(
        recent_on_time_rate=100.0, recent_order_count=MIN_ORDERS_PER_WINDOW - 1,
        prior_on_time_rate=100.0, prior_order_count=MIN_ORDERS_PER_WINDOW,
    )
    assert result == "Insufficient data"
