import importlib

import pytest


@pytest.fixture()
def fresh_db(tmp_path, monkeypatch):
    """Point the db module at a temporary SQLite file so tests don't
    touch the real database, then reload dependent modules so they
    pick up the patched path."""
    import backend.database.db as db_module

    monkeypatch.setattr(db_module, "DB_PATH", tmp_path / "test.db")
    db_module.init_db()

    import backend.models.readings as readings_module
    import backend.services.monitoring as monitoring_module

    importlib.reload(readings_module)
    importlib.reload(monitoring_module)

    # Reset in-memory state between tests
    monitoring_module._recent_values.clear()
    monitoring_module._last_status.clear()

    return monitoring_module


def test_process_reading_persists_and_classifies(fresh_db):
    monitoring = fresh_db
    reading = {
        "device_id": "ESP32_TEST",
        "shelf_id": "SHELF_TEST",
        "sensor_type": "ultrasonic",
        "distance_cm": 2.0,
        "timestamp": "2026-09-14T12:00:00",
    }
    result = monitoring.process_reading(reading)
    assert result["status"] == "FULL"
    assert result["shelf_id"] == "SHELF_TEST"
    assert result["previous_status"] is None


def test_process_reading_tracks_previous_status(fresh_db):
    monitoring = fresh_db
    base = {
        "device_id": "ESP32_TEST",
        "shelf_id": "SHELF_TEST",
        "sensor_type": "ultrasonic",
        "timestamp": "2026-09-14T12:00:00",
    }
    monitoring.process_reading({**base, "distance_cm": 2.0})
    second = monitoring.process_reading({**base, "distance_cm": 30.0})
    assert second["previous_status"] == "FULL"


def test_process_reading_missing_shelf_id_raises(fresh_db):
    monitoring = fresh_db
    with pytest.raises(KeyError):
        monitoring.process_reading({
            "device_id": "ESP32_TEST",
            "distance_cm": 2.0,
        })
