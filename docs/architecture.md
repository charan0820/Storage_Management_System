# StoreWatch Architecture

## Pipeline

```
Retail Shelf → Sensors → ESP32 → Wi-Fi → Backend/MQTT → StoreWatch Processing
→ Dashboard → Low Stock / Empty Shelf Alert
```

## Four layers

```
┌─────────────────────────┐
│       Hardware          │   Sensors + ESP32
├─────────────────────────┤
│     Communication       │   MQTT / HTTP
├─────────────────────────┤
│     Application         │   Database + Logic (source of truth)
├─────────────────────────┤
│      Presentation       │   Dashboard + Alerts
└─────────────────────────┘
```

Rules:
- The ESP32 does **not** contain dashboard or classification logic — it
  only reads and (optionally) filters sensor values, then publishes them.
- The dashboard does **not** read GPIO or the database directly — it
  only calls the backend API.
- The **backend is the single source of truth** for shelf status.
- Communication uses a **fixed telemetry format**, so hardware and
  software can be developed independently and either side can be
  swapped (e.g. ultrasonic → camera, ESP32 → Raspberry Pi) without
  rewriting the rest of the system.

## Telemetry contract (raw, from ESP32)

```json
{
  "device_id": "ESP32_01",
  "shelf_id": "SHELF_01",
  "sensor_type": "ultrasonic",
  "distance_cm": 8.4,
  "timestamp": "2026-09-14T18:30:00"
}
```

`timestamp` is optional in the request; the backend fills it in with the
current UTC time if omitted (useful for firmware without an RTC).

## Processed reading (backend output / stored)

```json
{
  "device_id": "ESP32_01",
  "shelf_id": "SHELF_01",
  "sensor_type": "ultrasonic",
  "sensor_value": 8.4,
  "filtered_value": 8.7,
  "status": "LOW_STOCK",
  "timestamp": "2026-09-14T18:30:00"
}
```

## Core interfaces (Section 13)

| Interface | Language | Location |
|---|---|---|
| `float readDistance()` | C++ | `firmware/esp32/sensors.h` |
| `filter_sensor_data(values)` | Python | `backend/services/monitoring.py` |
| `classify_shelf(distance)` | Python | `backend/services/monitoring.py` |
| `process_reading(reading)` | Python | `backend/services/monitoring.py` |
| `generate_alert(shelf_id, status)` | Python | `backend/services/alert_service.py` |
| `save_reading(reading)` | Python | `backend/models/readings.py` |

## API endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness check |
| POST | `/api/readings` | Ingest one telemetry reading |
| GET | `/api/readings` | Latest reading per shelf |
| GET | `/api/readings/<shelf_id>` | Latest reading for one shelf |
| GET | `/api/readings/<shelf_id>/history` | Reading history for charts |
| GET | `/api/alerts` | Active (unresolved) alerts |
| POST | `/api/alerts/<id>/resolve` | Manually resolve an alert |
| GET | `/api/devices` | ONLINE/OFFLINE status per device |

## Database schema

**sensor_readings**: `id, device_id, shelf_id, sensor_type, sensor_value, filtered_value, status, timestamp`

**alerts**: `id, shelf_id, alert_type, message, created_at, resolved`

## Shelf statuses

`FULL`, `LOW_STOCK`, `EMPTY`, `UNKNOWN`

`UNKNOWN` is used whenever the sensor fails or disconnects — it must
never silently become `EMPTY`.

## Alert deduplication

An alert is only created on the transition **into** `LOW_STOCK`/`EMPTY`.
Repeated readings in the same bad state do not create new alerts. The
open alert is auto-resolved when the shelf returns to `FULL`. See
`backend/services/alert_service.py`.

## Limitations

1. A single distance sensor cannot precisely determine exact product
   quantity — it estimates occupancy, not a unit count.
2. Readings can be affected by product geometry and placement.
3. The prototype monitors predefined shelf/product locations
   (`config.yaml`) rather than identifying arbitrary products.
4. Real deployment would require per-shelf/per-product calibration.
5. Network outages affect real-time monitoring; `UNKNOWN`/`OFFLINE`
   states exist to make this visible rather than hidden.
6. Industrial deployment would need more robust hardware and security
   (TLS on MQTT, device auth, etc.) — out of scope for this prototype.

## Future scope

Computer vision for product identification, RFID-based tracking,
weight-based quantity estimation, multi-store cloud architecture,
predictive restocking from historical demand, and a mobile app with
push notifications.
