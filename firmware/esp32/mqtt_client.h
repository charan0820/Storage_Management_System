#ifndef MQTT_CLIENT_H
#define MQTT_CLIENT_H

#include <Arduino.h>

// Connects Wi-Fi and MQTT. Call once from setup().
void setupConnectivity();

// Ensures Wi-Fi/MQTT are still connected; call every loop() iteration
// before publishing.
void ensureConnected();

// Publishes a single telemetry reading as JSON matching the fixed
// telemetry format defined in docs/architecture.md:
// { "device_id", "shelf_id", "sensor_type", "distance_cm", "timestamp" }
void publishReading(const char *deviceId, const char *shelfId,
                     const char *sensorType, float distanceCm);

#endif // MQTT_CLIENT_H
