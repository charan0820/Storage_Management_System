"""Core StoreWatch processing pipeline:

    Raw Sensor Data -> Filtering -> Calibration -> Status Classification

Interfaces here follow Section 13 of the spec:
    filter_sensor_data(values)
    classify_shelf(distance)
    process_reading(reading)
"""

from collections import defaultdict
from datetime import datetime, timezone

from backend.models.readings import Reading, save_reading

# --- Configuration (mirror config.yaml; see Section 6) ---
# TODO: load these from config.yaml instead of hardcoding once calibrated.
FULL_MAX_CM = 5
LOW_STOCK_MAX_CM = 20
MOVING_AVERAGE_WINDOW = 5

# Per-shelf rolling window of recent raw values, used for filtering.
# NOTE: in-memory only — fine for a single-process prototype. A
# multi-worker deployment would need this backed by shared state.
_recent_values: dict[str, list[float]] = defaultdict(list)

# Per-shelf last known status, used for alert deduplication
# (services/alert_service.py) and to detect state transitions.
_last_status: dict[str, str] = {}


def filter_sensor_data(values: list[float]) -> float:
    """Apply a simple moving average to reduce sensor noise (Section 7).

    Expects the most recent value last. Returns the averaged value.
    """
    if not values:
        raise ValueError("filter_sensor_data() called with no values")
    window = values[-MOVING_AVERAGE_WINDOW:]
    return sum(window) / len(window)


def classify_shelf(distance: float) -> str:
    """Map a filtered distance reading to a shelf status (Section 6/16).

    Returns one of: FULL, LOW_STOCK, EMPTY, UNKNOWN.
    A negative distance signals a sensor failure -> UNKNOWN, never EMPTY.
    """
    if distance is None or distance < 0:
        return "UNKNOWN"
    if distance < FULL_MAX_CM:
        return "FULL"
    if distance < LOW_STOCK_MAX_CM:
        return "LOW_STOCK"
    return "EMPTY"


def process_reading(reading: dict) -> dict:
    """Take a raw telemetry payload (Section 14) and turn it into a
    persisted, classified reading.

    Input shape (from ESP32 / sample_readings.csv):
        { device_id, shelf_id, sensor_type, distance_cm, timestamp }

    Returns the processed reading as a dict, matching:
        { device_id, shelf_id, sensor_value, filtered_value, status, timestamp }
    """
    shelf_id = reading["shelf_id"]
    raw_value = float(reading["distance_cm"])

    _recent_values[shelf_id].append(raw_value)
    # Cap window growth
    if len(_recent_values[shelf_id]) > MOVING_AVERAGE_WINDOW:
        _recent_values[shelf_id] = _recent_values[shelf_id][-MOVING_AVERAGE_WINDOW:]

    filtered_value = filter_sensor_data(_recent_values[shelf_id])
    status = classify_shelf(filtered_value if raw_value >= 0 else -1)

    timestamp = reading.get("timestamp") or datetime.now(timezone.utc).isoformat()

    processed = Reading(
        device_id=reading["device_id"],
        shelf_id=shelf_id,
        sensor_type=reading.get("sensor_type", "unknown"),
        sensor_value=raw_value,
        filtered_value=filtered_value,
        status=status,
        timestamp=timestamp,
    )
    save_reading(processed)

    previous_status = _last_status.get(shelf_id)
    _last_status[shelf_id] = status

    result = asdict_reading(processed)
    result["previous_status"] = previous_status
    return result


def asdict_reading(reading: Reading) -> dict:
    return {
        "device_id": reading.device_id,
        "shelf_id": reading.shelf_id,
        "sensor_type": reading.sensor_type,
        "sensor_value": reading.sensor_value,
        "filtered_value": reading.filtered_value,
        "status": reading.status,
        "timestamp": reading.timestamp,
    }
