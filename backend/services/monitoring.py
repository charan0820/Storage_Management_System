"""Core StoreWatch processing pipeline:

    Raw Sensor Data -> Filtering -> Calibration -> Status Classification

Interfaces here follow Section 13 of the spec:
    filter_sensor_data(values)
    classify_shelf(distance)
    process_reading(reading)
"""

from collections import defaultdict
import math
import threading
from functools import wraps
from backend.config import CONFIG, OFFLINE_SECONDS
from backend.database.db import get_connection
from datetime import datetime, timezone

from backend.models.readings import Reading, save_reading

# --- Configuration (mirror config.yaml; see Section 6) ---
# Legacy unconfigured shelf thresholds; registered shelves use SQLite calibration.
FULL_MAX_CM = CONFIG["thresholds"]["full_max_cm"]
LOW_STOCK_MAX_CM = CONFIG["thresholds"]["low_stock_max_cm"]
MOVING_AVERAGE_WINDOW = CONFIG["filtering"]["moving_average_window"]
_lock = threading.RLock()

# Per-shelf rolling window of recent raw values, used for filtering.
# NOTE: in-memory only — fine for a single-process prototype. A
# multi-worker deployment would need this backed by shared state.
_recent_values: dict[str, list[float]] = defaultdict(list)

# Per-shelf last known status, used for alert deduplication
# (services/alert_service.py) and to detect state transitions.
_last_status: dict[str, str] = {}
_sources = {}


def synchronized(function):
    """Serialize row settings and ingestion so a sample cannot use old calibration."""
    @wraps(function)
    def wrapped(*args, **kwargs):
        with _lock:
            return function(*args, **kwargs)
    return wrapped


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
    if isinstance(reading['distance_cm'], bool):
        raise ValueError('distance_cm must be a number, not a boolean')
    raw_value = float(reading["distance_cm"])

    if not isinstance(shelf_id, str) or not shelf_id.strip() or len(shelf_id) > 64:
        raise ValueError("shelf_id must be a nonempty string up to 64 characters")
    if not isinstance(reading["device_id"], str) or not reading["device_id"].strip():
        raise ValueError("device_id must be a nonempty string")
    if not math.isfinite(raw_value) or (raw_value != -1 and not 2 <= raw_value <= 400):
        raise ValueError("distance_cm must be 2..400 cm, or -1 for a sensor fault")
    sensor_type = reading.get("sensor_type", "unknown")
    if sensor_type not in {"ultrasonic", "simulated", "unknown"}:
        raise ValueError("Invalid sensor_type")
    conn = get_connection()
    try:
        shelf = conn.execute("SELECT * FROM shelves WHERE shelf_id=?", (shelf_id,)).fetchone()
    finally:
        conn.close()
    if shelf and shelf["device_id"] != reading["device_id"]:
        raise ValueError("Device is not assigned to this shelf")
    if shelf and not shelf['active']:
        raise ValueError('This row is retired')
    if shelf:
        for key in ('sensor_id', 'product_tag'):
            if key in reading and reading[key] != shelf[key]:
                raise ValueError(f'{key} does not match assignment; refresh device config')
    # Firmware omits timestamp. Legacy ISO timestamps remain accepted; reject uptime.
    timestamp = reading.get("timestamp") or datetime.now(timezone.utc).isoformat()
    try:
        parsed = datetime.fromisoformat(timestamp)
    except (ValueError, TypeError):
        raise ValueError("timestamp must be an ISO-8601 string, not device uptime")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    if parsed > datetime.now(timezone.utc):
        raise ValueError("timestamp cannot be in the future")
    timestamp = parsed.astimezone(timezone.utc).isoformat()
    current = ((datetime.now(timezone.utc) - parsed).total_seconds() <= OFFLINE_SECONDS
               and (not shelf or not shelf['updated_at'] or timestamp > shelf['updated_at']))

    # Faults must never pollute the filter or imply a restock.
    with _lock:
        # Keep historical imports without feeding them into the live filter.
        window = _recent_values[shelf_id] if current else []
        if raw_value < 0:
            window.clear()
            filtered_value, status = -1.0, "UNKNOWN"
        else:
            # Do not mix simulator readings with hardware or across long outages.
            key = (reading["device_id"], sensor_type)
            now_s = datetime.now(timezone.utc).timestamp()
            prior = _sources.get(shelf_id)
            if prior is None or prior[0] != key or now_s - prior[1] > OFFLINE_SECONDS:
                window.clear()
            if current:
                _sources[shelf_id] = (key, now_s)
            window.append(raw_value)
            del window[:-MOVING_AVERAGE_WINDOW]
            filtered_value = filter_sensor_data(window)
            status = classify_shelf(filtered_value)
            if shelf:
                status = "UNCALIBRATED"
                if shelf["calibrated"]:
                    fill = max(0, min(100, 100 * (shelf["empty_cm"] - filtered_value) /
                                                 (shelf["empty_cm"] - shelf["full_cm"])))
                    status = "EMPTY" if fill <= 5 else "LOW_STOCK" if fill <= shelf["low_percent"] else "FULL" if fill >= 90 else "NORMAL"

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
