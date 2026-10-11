#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include "sensors.h"
#include "secrets.h"

static const char *SHELF_IDS[] = {"SHELF_01", "SHELF_02", "SHELF_03"};
static unsigned long lastCycle = 0;

void setup() {
  Serial.begin(115200);
  initSensor();
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
}

void loop() {
  if (millis() - lastCycle < 2000) { delay(10); return; }
  lastCycle = millis();
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("Wi-Fi unavailable; dashboard will become OFFLINE.");
    WiFi.reconnect();
    return;
  }
  for (int i = 0; i < SENSOR_COUNT; ++i) {
    float distance = readDistance(i);
    // Sensor triggers never overlap: quiet time >= 65 ms between pings.
    delay(65);
    if (distance < 0) { distance = readDistance(i); delay(65); }
    char payload[192];
    snprintf(payload, sizeof(payload),
      "{\"device_id\":\"ESP32_01\",\"shelf_id\":\"%s\",\"sensor_type\":\"ultrasonic\",\"distance_cm\":%.2f}",
      SHELF_IDS[i], distance);
    WiFiClient transport;
    HTTPClient http;
    http.setConnectTimeout(1000);
    http.setTimeout(1500);
    if (http.begin(transport, BACKEND_URL)) {
      http.addHeader("Content-Type", "application/json");
      if (strlen(API_KEY)) http.addHeader("X-API-Key", API_KEY);
      int code = http.POST((uint8_t*)payload, strlen(payload));
      Serial.printf("%s %.2f cm -> HTTP %d\n", SHELF_IDS[i], distance, code);
      if (code != 201) Serial.println(http.getString());
      http.end();
    }
  }
}
