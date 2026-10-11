#include <Arduino.h>
#include "sensors.h"
static const int TRIG_PINS[SENSOR_COUNT] = {25, 26, 27};
static const int ECHO_PINS[SENSOR_COUNT] = {32, 33, 34};
void initSensor() {
  for (int i = 0; i < SENSOR_COUNT; ++i) {
    pinMode(TRIG_PINS[i], OUTPUT);
    pinMode(ECHO_PINS[i], INPUT);
    digitalWrite(TRIG_PINS[i], LOW);
  }
}
float readDistance(int index) {
  digitalWrite(TRIG_PINS[index], LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PINS[index], HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PINS[index], LOW);
  unsigned long duration = pulseIn(ECHO_PINS[index], HIGH, 25000UL);
  if (!duration) return -1.0f;
  float cm = duration * 0.0343f / 2.0f;
  return (cm >= 2 && cm <= 400) ? cm : -1.0f;
}
