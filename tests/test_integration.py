"""Day 7 integration milestone: Physical Shelf -> Sensor -> ESP32 ->
Wi-Fi -> Backend -> Database -> Shelf Status, simulated via the HTTP
ingestion path (same payload shape the ESP32/MQTT bridge produces)."""

from backend.app import app


def test_end_to_end_reading_produces_status():
    client = app.test_client()

    assert client.get("/health").status_code == 200

    r = client.post(
        "/api/readings",
        json={
            "device_id": "ESP32_01",
            "shelf_id": "SHELF_01",
            "sensor_type": "ultrasonic",
            "distance_cm": 3.0,
        },
    )
    assert r.status_code == 201
    assert r.json["status"] == "FULL"

    readings = client.get("/api/readings")
    assert readings.status_code == 200
    assert any(x["shelf_id"] == "SHELF_01" for x in readings.json)


def test_invalid_reading_missing_fields_rejected():
    client = app.test_client()
    r = client.post("/api/readings", json={"device_id": "ESP32_01"})
    assert r.status_code == 400
