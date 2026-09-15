#ifndef SENSORS_H
#define SENSORS_H

// Interface for shelf sensor reading.
// Keep this stable — the rest of the firmware and the telemetry format
// depend on it, not on how the sensor is physically implemented.
// See Section 13 of the project spec.

// Initialize sensor pins/peripherals. Call once from setup().
void initSensor();

// Take a single distance reading in centimeters.
// Returns -1.0 on read failure (e.g. timeout / no echo).
float readDistance();

#endif // SENSORS_H
