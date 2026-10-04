#include <Arduino.h>
#include "sensors.h"

// Wiring (HC-SR04 style ultrasonic sensor) — see docs/hardware.md
static const int TRIG_PIN = 5;
static const int ECHO_PIN = 18;

// Max distance we bother measuring. Anything beyond this is treated as
// "no product detected" territory anyway.
static const unsigned long TIMEOUT_US = 30000UL; // ~5m round trip

// Calibration offset (cm), measured empirically per Section 6: place an
// object at a known distance, compare to raw reading, set the delta here.
// Corrects for sensor mounting offset / housing thickness.
static const float CALIBRATION_OFFSET_CM = 0.0f; // TODO: set from bench test

void initSensor() {
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  digitalWrite(TRIG_PIN, LOW);
}

float readDistance() {
  // Send a 10us trigger pulse
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  unsigned long duration = pulseIn(ECHO_PIN, HIGH, TIMEOUT_US);

  if (duration == 0) {
    // No echo received within timeout -> sensor failure / out of range
    return -1.0;
  }

  // Speed of sound ~0.0343 cm/us, divide by 2 for round trip
  float distanceCm = (duration * 0.0343f) / 2.0f;
  return distanceCm + CALIBRATION_OFFSET_CM;
}
