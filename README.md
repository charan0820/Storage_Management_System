# StoreWatch — low-budget multi-shelf IoT prototype

An extension of the original Flask / SQLite project for a semester demonstration.
**One ESP32 DevKit + three HC-SR04 sensors monitor three separately assigned product shelves.**
No cloud subscription, MQTT broker, extra screen or Raspberry Pi required.

## Start the application (Windows / Linux / macOS)
Run commands from this project directory, with Python 3.10+:

```bash
python -m pip install -r requirements-device.txt
python -m backend.app
```
Open **http://localhost:5000**. Keep this terminal running.
The browser dashboard and API use the same server. Updates arrive approximately
 every 2 seconds on a healthy network. All settings and telemetry persist in SQLite.

## Try the complete setup without hardware
In a second terminal:

```bash
python scripts/simulate.py --calibrate-demo
```
This sets **synthetic** 5 cm full / 30 cm empty calibration for all three shelves,
then cycles them independently through stock levels. Cards explicitly say SIMULATED DATA.
Other test modes:

```bash
python scripts/simulate.py --scenario empty --cycles 10
python scripts/simulate.py --scenario fault --cycles 5
python scripts/simulate.py --scenario full --cycles 10
```
Stop with Ctrl+C. Shelves become OFFLINE after 60 seconds without telemetry.
Do not run the simulator and ESP32 simultaneously. Replace synthetic calibration
with your own measurements before using real hardware.

## Connect the actual ESP32
1. Build the three-shelf rig using [docs/hardware.md](docs/hardware.md) and [docs/wiring.svg](docs/wiring.svg).
2. Connect laptop and ESP32 to the same **2.4 GHz Wi-Fi**. Avoid guest networks with client isolation.
3. Install VS Code + PlatformIO extension. Open `firmware/esp32` as a project.
4. Copy `secrets.example.h` to `secrets.h`. Enter Wi-Fi credentials and set
   `BACKEND_URL` to `http://YOUR_LAPTOP_IPV4:5000/api/readings`. On Windows find IPv4
   with `ipconfig`; on Linux use `hostname -I`. `localhost` on ESP32 does not mean the laptop.
5. Select ESP32 Dev Module (`esp32dev`), plug in USB, then Build / Upload / Monitor.
   The serial monitor should print `SHELF_01 ... -> HTTP 201` for each sensor.
   If upload stalls, hold BOOT while upload begins and release once connected.
6. Allow Python inbound TCP 5000 on your **private** network if the OS firewall prompts.
7. Stop the simulator. Use **Assign / calibrate** on each card to enter the product name,
   measured full and empty distances, and low-stock percentage.
8. Remove products in the chosen controlled geometry and watch the card / restock queue update.

Optional CLI firmware commands (from `firmware/esp32`):
```bash
python -m platformio run
python -m platformio run --target upload
python -m platformio device monitor
```

## Included behavior
- Independent product assignment and calibration for each shelf.
- Full / in-stock / low / empty classification and approximate fill percentage.
- Backend moving average over five valid readings; no duplicate firmware averaging.
- Sensor faults and offline states never become empty-stock estimates.
- Restock alert deduplication, low→empty escalation, recovery resolution.
- Last 50 samples chart and persistent history; calibration changes preserve history.
- Waiting and uncalibrated shelves appear even before telemetry arrives.
- Visible simulated-versus-hardware source labels.
- Three sequential ultrasonic pings with quiet gaps to reduce crosstalk.
- Optional write authentication: set `STOREWATCH_API_KEY` before starting the backend
  and enter the same key in firmware / calibration dialog / simulator environment.
  Linux: `export STOREWATCH_API_KEY=your-key`; Windows PowerShell:
  `$env:STOREWATCH_API_KEY="your-key"`. Default is open for a trusted LAN demo.

## What the sensor actually measures
Ultrasonic ranging observes the nearest reflecting surface in its beam, not every
item on a shelf. The inexpensive demonstration uses a **vertical stack of identical
flat packets or boxes in each compartment**, with a downward-facing sensor above it.
A growing stack gives a smaller distance. Empty shelf gives the largest distance.
Loose bottles side by side can remain the same height as stock is removed and will
not yield reliable fill estimates. Use a guided lane / constrained stack; label
outputs as estimates and explain this limitation in the presentation.

For a bigger store, use one sensor per lane you want to observe, and more ESP32
boards for extra groups of shelves. Product assignment is manual, not recognition.

## Validation and documentation
```bash
python -m pytest -q
```
- [Hardware, mounting, costs and connections](docs/hardware.md)
- [Visual wiring diagram](docs/wiring.svg)
- [Architecture and stock model](docs/architecture.md)
- [API contract](docs/api.md)
- [Demo and physical verification checklist](docs/testing.md)

Use `requirements-device.txt` for this lean application. `requirements.txt` retains
optional analytics and legacy Streamlit / MQTT dependencies. The old MQTT client
files are retained for reference and excluded from the firmware build. HTTP is the
working default. Run a single backend process; in-memory filtering is per process.
This is a local prototype, not a publicly exposed production server.
