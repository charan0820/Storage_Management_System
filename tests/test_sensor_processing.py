from backend.services.monitoring import filter_sensor_data, classify_shelf


def test_filter_sensor_data_averages_window():
    assert filter_sensor_data([10, 10, 10]) == 10
    assert filter_sensor_data([0, 10]) == 5


def test_filter_sensor_data_uses_most_recent_window_only():
    # window size is 5 by default; only the last 5 values should count
    values = [100, 100, 100, 3, 3, 3, 3, 3]
    assert filter_sensor_data(values) == 3


def test_filter_sensor_data_empty_raises():
    try:
        filter_sensor_data([])
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_classify_shelf_full():
    assert classify_shelf(2.0) == "FULL"


def test_classify_shelf_low_stock():
    assert classify_shelf(10.0) == "LOW_STOCK"


def test_classify_shelf_empty():
    assert classify_shelf(30.0) == "EMPTY"


def test_classify_shelf_unknown_on_negative():
    assert classify_shelf(-1.0) == "UNKNOWN"


def test_classify_shelf_unknown_on_none():
    assert classify_shelf(None) == "UNKNOWN"
