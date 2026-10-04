# StoreWatch

IoT smart shelf monitoring: ESP32 + ultrasonic sensor → MQTT/HTTP → Flask backend → SQLite → Streamlit dashboard, with low-stock/empty alerts.

## Run

```bash
pip install -r requirements.txt
python backend/app.py          # backend on :5000
streamlit run dashboard/app.py # dashboard
```

Firmware: open `firmware/esp32/` in PlatformIO, set Wi-Fi/broker credentials in `mqtt_client.cpp`, flash to an ESP32.

No hardware yet? Load `data/sample_readings.csv` via `data/load_sample_data.py`, or POST to `/api/readings` directly.

## Docs
- `docs/architecture.md` — system architecture
- `docs/hardware.md` — wiring and calibration
- `docs/api.md` — API reference
- `docs/testing.md` — sensor test log

## Test
```bash
python -m pytest -q
```
