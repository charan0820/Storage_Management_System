# StoreWatch Hardware

## Required components

- ESP32 dev board
- Ultrasonic sensor (HC-SR04) OR IR distance sensor
- Breadboard
- Jumper wires
- USB power supply

## Optional components

- Load cell + HX711 (weight-based extension)
- LED / buzzer (local alert indicator)
- OLED display (on-device status)
- Servo
- DHT11/DHT22 (temperature/humidity, not core to shelf monitoring)

## Recommended sensor: ultrasonic (HC-SR04)

Simple, cheap, easy to demonstrate live. Measures distance from the
sensor (mounted above/behind the shelf) down to the nearest product or
the shelf floor.

### Wiring (HC-SR04 → ESP32)

| HC-SR04 pin | ESP32 pin |
|---|---|
| VCC | 5V (or 3.3V-tolerant variant) |
| GND | GND |
| TRIG | GPIO 5 |
| ECHO | GPIO 18 (use a voltage divider if the sensor is 5V logic) |

These pin numbers match `firmware/esp32/sensors.cpp` — update both if
you wire it differently.

### How it works

```
Shelf
────────────────────
      Product
         ↓
      Sensor
         ↓
    Distance
```

As products are removed, the measured distance increases. The firmware
sends raw + filtered distance; the **backend** decides FULL/LOW_STOCK/
EMPTY, not the firmware (see `docs/architecture.md`).

## Alternative: weight-based (load cell + HX711)

More technically interesting but needs calibration per shelf/product
weight. Recommended only as an extension if a load cell is already on
hand — not the primary path for a 2-week timeline.

```
Load Cell → HX711 → ESP32

Shelf weight = 5 kg
Average product weight = 0.5 kg
Estimated quantity ≈ 10
```

## Calibration

Thresholds in `config.yaml` (`thresholds.full_max_cm`,
`thresholds.low_stock_max_cm`) are placeholders. To calibrate:

1. Place a full shelf in front of the sensor, record the distance.
2. Remove products incrementally, recording distance at each stage.
3. Pick thresholds that separate FULL / LOW_STOCK / EMPTY based on the
   actual measured ranges — not guessed values.
4. Update `config.yaml` and `backend/services/monitoring.py`.

## Sensor failure handling

If the sensor returns no echo (timeout), `readDistance()` returns `-1.0`.
This is published as-is; the backend maps any negative value to
`UNKNOWN`, never to `EMPTY` (a disconnected sensor is not the same as
an empty shelf).

## Multi-shelf simulation

With one physical sensor, additional shelves can be simulated using
`data/sample_readings.csv` and `data/load_sample_data.py` to demonstrate
a full store on the dashboard. Simulated data must be clearly
distinguished from real sensor data (see `sensor_type: "simulated"` in
`config.yaml`) and never presented as a live measurement.
