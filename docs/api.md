# StoreWatch API

Base URL: `http://localhost:5000`

| Method | Path                          | Description                         |
|--------|-------------------------------|--------------------------------------|
| GET    | `/health`                     | Liveness check                       |
| POST   | `/api/readings`                | Ingest one telemetry reading         |
| GET    | `/api/readings`                | Latest reading per shelf             |
| GET    | `/api/readings/<shelf_id>`     | Latest reading for one shelf         |
| GET    | `/api/readings/<shelf_id>/history` | Recent history for one shelf (`?limit=200`) |
| GET    | `/api/alerts`                  | Active (unresolved) alerts           |
| POST   | `/api/alerts/<id>/resolve`     | Manually resolve an alert            |
| GET    | `/api/devices`                 | Per-shelf ONLINE/OFFLINE status      |

### POST /api/readings
Request body:
```json
{
  "device_id": "ESP32_01",
  "shelf_id": "SHELF_01",
  "sensor_type": "ultrasonic",
  "distance_cm": 8.4,
  "timestamp": "2026-09-14T18:30:00"
}
```
`timestamp` is optional (server time used if omitted). Returns `201` with the processed reading, or `400` on missing `device_id`/`shelf_id`/`distance_cm`.
