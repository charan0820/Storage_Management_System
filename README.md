# StoreWatch — two-row grocery shelf prototype

A functional Flask / SQLite app for **one cardboard shelf with two 30 cm product
rows**, one ultrasonic sensor per row, controlled by one classic ESP32 DevKit.
No cloud, MQTT broker or Raspberry Pi required.

## Start

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-device.txt
.venv\Scripts\python.exe -m backend.app
```

Open **http://localhost:5000**. The dashboard, API, simulator controls and hardware
guide share the same server. Keep it running; updates poll every two seconds.

## Try it before building

In the dashboard's **Test bench**, select a row, click **Use demo calibration**, then
send simulated distances. Try 5 cm (full), 26 cm (low), 30 cm (empty), and the sensor
fault checkbox. Repeat readings to settle the five-sample average. Demo calibration
and simulated data are labeled independently. Do not run physical telemetry while
simulating. Use Assign / calibrate to enter real measurements before the physical demo.

The CLI simulator is also available:

```powershell
python scripts/simulate.py --calibrate-demo --cycles 10
python scripts/simulate.py --scenario empty --cycles 6
python scripts/simulate.py --scenario fault --cycles 2
```

## Hardware and final setup

Read the **[complete hardware build and setup guide](docs/hardware.md)**, also
available at **http://localhost:5000/setup-guide**. It includes the parts list,
cardboard dimensions, sensor placement, electrical details, firmware flashing,
Wi-Fi configuration, calibration and a physical acceptance checklist.

- [Two-sensor connection map](docs/wiring.svg)
- [Cardboard prototype layout](docs/prototype.svg)

| Location | Channel ID | Sensor | TRIG | ECHO through its own divider |
|---|---|---|---:|---:|
| RACK_01 / Row 1 | SHELF_01 | US_01 | GPIO25 | GPIO32 |
| RACK_01 / Row 2 | SHELF_02 | US_02 | GPIO26 | GPIO33 |

Each HC-SR04 uses regulated 5 V and common GND. **Never connect its 5 V Echo directly
to ESP32**: ECHO → 1 kΩ → GPIO junction → 2 kΩ → GND. Check the board power pin and
actual divider voltage; full instructions and primary references are in the guide.

## Product tags and controller behavior

Use **Assign / calibrate** to enter a printed SKU/barcode and product name on a row.
Tags are manual assignments, optionally typed by a USB barcode scanner connected to
the laptop. No RFID hardware is included. Ultrasonic ranging cannot identify products.
The ESP32 fetches `/api/devices/ESP32_01/config` at startup and every ten seconds;
it learns sensor → shelf → row → product tag and includes sensor/tag IDs in telemetry.
Wrong devices, sensors, stale tags and unregistered/retired channels are rejected.

Open `firmware/esp32` in PlatformIO. Copy `secrets.example.h` to `secrets.h`, enter
Wi-Fi credentials and `http://LAPTOP_IPV4:5000/api/readings`, build/upload and watch
serial output at 115200 baud. Use a shared 2.4 GHz LAN; localhost on the ESP32 is not
the laptop. Firmware dependencies are pinned in `platformio.ini`.

## What the stock estimate means

For the cardboard demo, use two guided lanes with products toward the front and a
flat sliding follower behind them. Rear-mounted sensors measure the distance to the
follower. Manually slide it against remaining products after removal. Calibrate the
full and empty stops; approximately 5 cm and 30 cm are examples, not actual measurements.
Loose bottles/packets without controlled geometry can return misleading echoes.
Outputs are **fill estimates, not exact item counts**. See the guide for an alternative
vertical-stack geometry and physical validation requirements.

Per-row calibration and tags, reading history and alerts persist in SQLite. Faults
never mean empty; offline rows lose their current fill estimate after 60 seconds.
Saving row settings retains history and clears alerts belonging to the old assignment.
Synthetic demo values are visibly labeled until replaced by measured calibration.
Existing databases migrate automatically; the old third demo channel is retired,
with its history retained. Existing product names and calibration values are preserved;
legacy calibration is marked as demo/unverified until measured on the new rig.

## Validation and configuration

```powershell
python -m pytest -q
node --check backend/static/app.js
```

- [Architecture](docs/architecture.md)
- [API](docs/api.md)
- [Testing and demo checklist](docs/testing.md)

Optional write key: set `STOREWATCH_API_KEY` before starting the server and use the
same value in firmware, simulator environment and browser settings/test bench. Default
is open for a trusted LAN demonstration. Read endpoints remain LAN-accessible.
Set `STOREWATCH_DB` to use a different SQLite file. Use one backend process because
filtering is in memory. This is a local prototype; physical accuracy must be verified
on your assembled rig. Legacy Streamlit/MQTT and analytics modules are retained for
reference; the supported application is the Flask dashboard at `/`.
