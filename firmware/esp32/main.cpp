#include <Arduino.h>
#include "sensors.h"
#include "mqtt_client.h"

// --- Identity ---
static const char *DEVICE_ID = "ESP32_01";
static const char *SHELF_ID = "SHELF_01";
static const char *SENSOR_TYPE = "ultrasonic";

// --- Timing ---
static const unsigned long READ_INTERVAL_MS = 2000; // one reading every 2s
static unsigned long lastReadTime = 0;

// --- Simple moving-average filter (see Section 7 of the spec) ---
static const int WINDOW_SIZE = 5;
static float readingWindow[WINDOW_SIZE];
static int windowIndex = 0;
static int windowFilled = 0;

static float filterReading(float newValue) {
  readingWindow[windowIndex] = newValue;
  windowIndex = (windowIndex + 1) % WINDOW_SIZE;
  if (windowFilled < WINDOW_SIZE) windowFilled++;

  float sum = 0;
  for (int i = 0; i < windowFilled; i++) sum += readingWindow[i];
  return sum / windowFilled;
}

void setup() {
  Serial.begin(115200);
  delay(500);

  initSensor();
  setupConnectivity();

  Serial.println("StoreWatch firmware started.");
}

void loop() {
  ensureConnected();

  unsigned long now = millis();
  if (now - lastReadTime < READ_INTERVAL_MS) {
    return;
  }
  lastReadTime = now;

  // Reliability: retry once before reporting a failed read, since a
  // single missed echo is common and shouldn't flip status to UNKNOWN.
  float raw = readDistance();
  if (raw < 0) {
    delay(50);
    raw = readDistance();
  }

  if (raw < 0) {
    // Sensor failure — publish a NaN-ish sentinel and let the backend
    // decide UNKNOWN status rather than guessing here (Section 16).
    Serial.println("Sensor read failed.");
    publishReading(DEVICE_ID, SHELF_ID, SENSOR_TYPE, -1.0);
    return;
  }

  float filtered = filterReading(raw);

  // NOTE: classification (FULL/LOW_STOCK/EMPTY) intentionally happens
  // in the backend, not here. The ESP32 only reports raw + filtered
  // sensor data. This keeps the hardware/software boundary clean
  // (Section 34 — ESP32 should not contain dashboard/business logic).
  Serial.printf("raw=%.2fcm filtered=%.2fcm\n", raw, filtered);

  publishReading(DEVICE_ID, SHELF_ID, SENSOR_TYPE, filtered);
}
