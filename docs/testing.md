# Test and semester demonstration

## Automated verification
Run from project root: `python -m pytest -q`. Tests isolate SQLite in temporary
folders and do not use the development database. Coverage includes independent
shelf calibration, missing / malformed JSON, invalid ranges and NaN, wrong devices,
faults and recovery, source switching, stale shelf health, retaining historical
readings across calibration, duplicate timestamps and serving dashboard assets.

## Verification performed for this extension
- Automated tests: **39 passed** on 11 October 2026.
- Real HTTP simulator → Flask → SQLite → shelf-summary round trip: passed for all three shelves.
- JavaScript syntax check (`node --check`): passed.
- Git whitespace check: passed.
- Wiring SVG rendered and visually inspected.
- Browser layout / interaction QA: not performed in this environment.
- Firmware build attempted with PlatformIO: not verified. The downloaded ESP32
  toolchain failed its checksum check; no unverified compiler package was accepted.
  Run PlatformIO Build on your laptop with a working package mirror before flashing.
- Physical ESP32 / sensors: not attached; not physically verified.

## Live software test
1. Start `python -m backend.app`.
2. Open `http://localhost:5000`.
3. Run `python scripts/simulate.py --calibrate-demo --cycles 5`.
4. Verify all three cards show SIMULATED DATA and separate stock levels.
5. Run `python scripts/simulate.py --scenario empty --cycles 6`.
6. Verify low/empty alerts after the filter settles.
7. Run `python scripts/simulate.py --scenario fault --cycles 2`.
8. Verify fault cards have no fill% and previous restock alerts remain.
9. Run `python scripts/simulate.py --scenario full --cycles 6`.
10. Verify measured recovery clears alerts. Stop telemetry and wait >60 seconds;
    all shelves should show Offline, with no current fill estimate.

## Physical test (not performed by the software author)
The project has no remotely attached physical rig. Compilation and software tests
cannot prove wiring, power stability, ranging accuracy or crosstalk performance.
Complete this table with your own measured data before the final demonstration.

| Shelf | Stack state | Ruler cm | Sensor cm | Expected state | Result / observation |
|---|---|---|---|---|---|
| 01 | Full | | | FULL | |
| 01 | Half | | | NORMAL | |
| 01 | Low | | | LOW_STOCK | |
| 01 | Empty | | | EMPTY | |
| 02 | Full / half / low / empty | | | | |
| 03 | Full / half / low / empty | | | | |

For every shelf, try at least 10 readings per state and record mean/range. Verify
divider junction voltages before connecting Echo to GPIO. Confirm all three sensor
IDs map to the right compartments by moving one target at a time. Check a sensor
with no reflecting target reports fault. Power off the whole board and verify
Offline after 60 seconds. Do not disconnect wires while powered for the demo.

## Presentation sequence (about 3 minutes)
- Explain one shelf → one manually assigned product → one sensor.
- Show full readings on three physical shelves (hardware source label).
- Remove packets from one compartment; show low-stock alert after settling.
- Empty it; show alert escalating to empty.
- Refill; show alert resolution.
- Turn off ESP32; explain Offline after 60 seconds.
- Explain the limitation: this monitors stack height, not exact grocery item count.

## Troubleshooting
- HTTP -1 / timeout: confirm laptop IPv4, firewall/private-network rule and Wi-Fi isolation.
- HTTP 401: API keys do not match.
- HTTP 400: inspect serial response; check shelf/device identity or invalid payload.
- Always no echo: check common ground, sensor 5 V supply, pins and divider; aim at flat target.
- Wrong shelf updates: swap the sensor wiring or correct its firmware mapping.
- Jumping readings: isolate sensor beams, stabilize mounts, move sidewalls out of beam.
- Uncalibrated: save measured full and empty distances for that shelf.
- Incorrect stock level: ensure geometry matches the stack model and recalibrate.
