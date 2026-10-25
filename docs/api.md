# HTTP API

The Flask server and dashboard share `http://LAPTOP_IP:5000`. Writes require
`X-API-Key` only when STOREWATCH_API_KEY is set. Read endpoints are public on the LAN.

| Method | Path | Purpose |
|---|---|---|
| GET | / | Main browser application |
| GET | /setup-guide | Printable hardware specifications, diagrams and final setup |
| GET | /hardware/hardware.md | Complete downloadable build instructions |
| GET | /health | Backend health |
| GET | /api/shelves | Active rows, tags, calibration, latest reading, stock estimate and health |
| PUT | /api/shelves/SHELF_01 | Assign product/tag and calibrate row |
| GET | /api/devices/ESP32_01/config | Controller manifest: sensor → shelf → row → product/tag |
| POST | /api/readings | Ingest one registered sensor sample; success 201 |
| GET | /api/readings | Latest sample per observed channel (legacy interface) |
| GET | /api/readings/SHELF_01 | Latest sample for channel |
| GET | /api/readings/SHELF_01/history?limit=50 | Oldest-first recent history; limit 1–2000 |
| GET | /api/devices | Telemetry channel health (legacy interface) |
| GET | /api/alerts | Active refill alerts |

SHELF_01 / SHELF_02 are historical API names for **rows**, both under RACK_01.
US_01 and US_02 identify physical sensor wiring. SHELF_03 is retired; history remains
readable. Add mappings to config.yaml and matching physical channels to extend the rig.

Telemetry (new firmware):

```json
{"device_id":"ESP32_01","shelf_id":"SHELF_01","sensor_id":"US_01","product_tag":"TEA-001","sensor_type":"ultrasonic","distance_cm":8.4}
```

Device, row and distance are required. Sensor and tag are optional for legacy clients;
when present they must match the assignment. Invalid/unregistered/retired channels,
wrong devices and mismatched tags/sensors return 400. No echo is `distance_cm: -1`.
Finite distances 2–400 cm are accepted; booleans, NaN and infinity are rejected.
`sensor_type: "simulated"` labels software samples. Hardware omits timestamp; server
records UTC. Optional ISO-8601 timestamps remain accepted for historical tests/imports;
numeric uptime and future times are rejected.

Row settings:

```json
{"product":"Tea boxes","product_tag":"TEA-001","full_cm":5,"empty_cm":30,"low_percent":25,"calibration_source":"measured"}
```

Product name: 1–80 characters; tag: 1–64 ASCII letters/digits, hyphens, dots or
underscores. A tag is a manually assigned SKU, not proof of physical product identity.
Require `2 <= full_cm < empty_cm <= 400` and `5 < low_percent < 90`.
Both distances initially mark the row calibrated. Source is `measured` or `demo`;
choose demo for synthetic distances. Saving retains history, resolves old refill
alerts, clears filtering, and waits for a fresh sample. Unknown/retired rows return 404.

The manifest returns `device_id` and `rows`, each with `shelf_id`, `parent_shelf`,
`row_number`, `sensor_id`, `product`, `product_tag`, `length_cm`, `updated_at`.
Firmware polls it at startup and every 10 seconds, matching fixed sensor IDs to pins.
A stale tag fails ingestion and triggers an early config refresh.

States: WAITING, UNCALIBRATED, FULL, NORMAL, LOW_STOCK, EMPTY, UNKNOWN, OFFLINE.
`fill_percent` is null without a valid recent calibrated reading. Calibration provenance
is independent from telemetry source: a hardware reading may still use demo calibration.
History includes previous assignments and calibration; chart labels explain this.
