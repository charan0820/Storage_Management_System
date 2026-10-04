from datetime import datetime, timedelta, timezone

from backend.app import app


def test_recent_reading_is_online():
    client = app.test_client()
    client.post(
        "/api/readings",
        json={
            "device_id": "ESP32_01",
            "shelf_id": "SHELF_ONLINE_TEST",
            "sensor_type": "ultrasonic",
            "distance_cm": 3.0,
        },
    )
    devices = client.get("/api/devices").json
    dev = next(d for d in devices if d["shelf_id"] == "SHELF_ONLINE_TEST")
    assert dev["status"] == "ONLINE"


def test_stale_reading_is_offline():
    client = app.test_client()
    stale_ts = (datetime.now(timezone.utc) - timedelta(seconds=120)).isoformat()
    client.post(
        "/api/readings",
        json={
            "device_id": "ESP32_02",
            "shelf_id": "SHELF_OFFLINE_TEST",
            "sensor_type": "ultrasonic",
            "distance_cm": 3.0,
            "timestamp": stale_ts,
        },
    )
    devices = client.get("/api/devices").json
    dev = next(d for d in devices if d["shelf_id"] == "SHELF_OFFLINE_TEST")
    assert dev["status"] == "OFFLINE"
