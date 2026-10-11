# HTTP API

Default origin: `http://LAPTOP_IP:5000`. JSON responses. Writes require `X-API-Key`
only if STOREWATCH_API_KEY is set. Dashboard polls from the same origin.

| Method | Path | Purpose |
|---|---|---|
| GET | / | Browser dashboard |
| GET | /health | Backend health |
| GET | /api/shelves | All configured shelves, product, calibration, latest reading, fill%, health |
| PUT | /api/shelves/SHELF_01 | Update product and/or calibration |
| POST | /api/readings | Ingest a single sensor reading; success 201 |
| GET | /api/readings | Latest reading per observed shelf (legacy interface) |
| GET | /api/readings/SHELF_01 | Latest reading for this shelf |
| GET | /api/readings/SHELF_01/history?limit=50 | History, oldest first (limit 1–2000) |
| GET | /api/devices | Health of shelves with telemetry (legacy interface) |
| GET | /api/alerts | Active restock alerts |

ESP32 payload:
```json
{"device_id":"ESP32_01","shelf_id":"SHELF_01","sensor_type":"ultrasonic","distance_cm":8.4}
```
Use `distance_cm: -1` for no echo / invalid range; use `sensor_type: "simulated"`
for software tests. ESP32 omits timestamp; server uses current UTC. Optional ISO-8601
timestamps are accepted for legacy tests/imports, but future timestamps and numeric
uptime are rejected. Invalid payloads return 400; assignment mismatch returns 400.
Legacy unconfigured shelf IDs are still ingested but do not appear in the configured
shelf dashboard. Add mappings in config.yaml and restart to add new shelf IDs.

Calibration payload:
```json
{"product":"Biscuits","full_cm":5,"empty_cm":30,"low_percent":25}
```
Require `2 <= full_cm < empty_cm <= 400`, and `5 < low_percent < 90`. Both distance
fields must be supplied together to initially mark the shelf calibrated. Product
name is 1–80 characters. Unknown shelf returns 404. Saving preserves history and
invalidates the live summary until a fresh reading is received.

Possible shelf states: WAITING, UNCALIBRATED, FULL, NORMAL, LOW_STOCK, EMPTY, UNKNOWN,
OFFLINE. `fill_percent` is null without a valid recent calibrated reading.
