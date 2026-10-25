# Verification and demonstration checklist

## Software checks completed on 22 October 2026

- **55 tests passed**, using the project .venv with requirements-device.txt installed.
- `node --check backend/static/app.js` passed.
- `git diff --check` passed (Git emits normal Windows line-ending notices).
- PlatformIO **release firmware build succeeded** for `esp32dev`, Espressif32 6.9.0,
  ArduinoJson 7.2.1. RAM 45,908 / 327,680 bytes (14.0%); flash 800,973 / 1,310,720
  bytes (61.1%). Build used the ignored secrets.h configuration; provide your own
  Wi-Fi credentials and laptop IP before flashing. No hardware was flashed.
- Browser checked at widths 320, 768, 1024 and 1440 pixels; no horizontal overflow.
  Dark theme was visually reviewed; the CSS includes light and dark system palettes.
- Browser interactions verified: row assignment save, invalid full/empty calibration,
  independent simulation, empty alert, fault preserving an existing alert, chart
  updates, loading/empty states, and full setup-guide navigation with both images loaded.
- GPIO diagram and cardboard layout rendered and visually reviewed. PNG wiring export
  now matches the current SVG. Dashboard screenshot is in `dashboard-preview.png`.
- Browser verification uses `data/prototype_demo.db`, separate from the original
  bundled database. The original database was restored after initial migration review.

Tests cover device health, independent calibration, simulated/hardware source switching,
fault and recovery, alert deduplication, malformed JSON/numbers/tags, sensor/tag identity,
reassignment, config manifests, history retention, legacy schema migration, archived
third-channel history, optional write authentication and setup-asset access restrictions.
Backdated samples cannot replace a fresh live reading, change current alerts or contaminate the live moving average.
Settings changes and ingestion share a lock to prevent use of an old calibration.

## Repeat checks

```powershell
.venv\Scripts\python.exe -m pytest -q
node --check backend/static/app.js
.venv\Scripts\python.exe -m platformio run -d firmware/esp32
```

## Browser demonstration

1. Start `.venv\Scripts\python.exe -m backend.app`; open http://localhost:5000.
2. Review the two product rows and open Assign / calibrate. Change a printed tag
   and name. Keep calibration type set to demo while using synthetic distances.
3. In Test bench, choose Row 1 and Use demo calibration. Send 5 cm (full), 26 cm
   (low), 30 cm (empty); repeat up to five samples per change for filtering to settle.
4. Repeat on Row 2 to show independent sensor channels.
5. Enable missing echo and send: show Sensor fault, no fill percentage, and retained
   refill alert. Disable it, send full samples, and show automatic alert resolution.
6. Stop sending samples; show OFFLINE after 60 seconds, with no current fill estimate.
7. Open Hardware & setup and the full guide to show wiring and cardboard construction.

## Physical checks still required

No ESP32/sensor rig is attached to this session. Successful compilation and software
simulation do not prove wiring, signal voltage, echo quality or mechanical repeatability.
Build using [hardware.md](hardware.md); inspect wiring with power unplugged. Measure
both divider junction voltages before connecting them to ESP32 inputs.

Record at least ten readings per state for both rows:

| Row | Follower state | Ruler distance | Sensor mean/range | Expected status | Observations |
|---|---|---|---|---|---|
| 1 | Full | | | FULL | |
| 1 | Half | | | NORMAL | |
| 1 | Low | | | LOW_STOCK | |
| 1 | Empty | | | EMPTY | |
| 2 | Full | | | FULL | |
| 2 | Half | | | NORMAL | |
| 2 | Low | | | LOW_STOCK | |
| 2 | Empty | | | EMPTY | |

Move one follower at a time to confirm physical sensor-to-row identity. Test no echo,
Wi-Fi loss, USB removal and reconnect. Replace synthetic calibration with measured
full/empty stops and verify settings persist after restarting the server.

## Troubleshooting

- HTTP timeout: check laptop IPv4, Wi-Fi client isolation and private-network firewall.
- HTTP 401: match the optional API key in server, browser and firmware.
- HTTP 400: inspect serial response; stale tags trigger config refresh, wrong sensor or
  device mappings are rejected. Old three-channel firmware must be replaced.
- No echoes: inspect 5 V supply, common ground, divider junctions, pin labels and target alignment.
- Jumping distances: stabilize mounts/followers and keep floor/dividers outside the beam.
- Wrong fill: confirm the follower moves against remaining products, then remeasure calibration.
- No product tag on board: verify `/api/devices/ESP32_01/config` and allow ~10 seconds to refresh.
- Readings become offline: individual test-bench sends are snapshots; send again or run
  the CLI simulator for sustained software telemetry. Stop it before hardware use.
