#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include "sensors.h"
#include "secrets.h"

static const char *DEVICE_ID = "ESP32_01";
static const char *SENSOR_IDS[] = {"US_01", "US_02"};
struct Assignment { String row; String tag; String product; };
static Assignment assigned[SENSOR_COUNT];
static unsigned long lastCycle = 0, lastConfig = 0;
static bool configured = false;

// BACKEND_URL retains the original /api/readings convention.
String configUrl() {
  String url(BACKEND_URL);
  int index = url.indexOf("/api/readings");
  if (index < 0) return "";
  return url.substring(0, index) + "/api/devices/" + DEVICE_ID + "/config";
}
bool fetchAssignments() {
  WiFiClient transport;
  HTTPClient http;
  http.setConnectTimeout(1000);
  http.setTimeout(1500);
  if (!http.begin(transport, configUrl())) return false;
  int code = http.GET();
  if (code != 200) { Serial.printf("Config HTTP %d\n", code); http.end(); return false; }
  JsonDocument doc;
  auto error = deserializeJson(doc, http.getString());
  http.end();
  if (error || !doc["rows"].is<JsonArray>()) return false;
  Assignment next[SENSOR_COUNT];
  bool found[SENSOR_COUNT] = {};
  for (JsonObject row : doc["rows"].as<JsonArray>()) {
    for (int i=0; i<SENSOR_COUNT; ++i) {
      if (String(row["sensor_id"] | "") == SENSOR_IDS[i]) {
        next[i].row = row["shelf_id"] | "";
        next[i].tag = row["product_tag"] | "";
        next[i].product = row["product"] | "";
        found[i] = next[i].row.length() && next[i].tag.length();
      }
    }
  }
  for (int i=0; i<SENSOR_COUNT; ++i) if (!found[i]) return false;
  for (int i=0; i<SENSOR_COUNT; ++i) {
    assigned[i] = next[i];
    Serial.printf("%s -> %s / %s / %s\n", SENSOR_IDS[i], assigned[i].row.c_str(), assigned[i].tag.c_str(), assigned[i].product.c_str());
  }
  return true;
}
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
    Serial.println("Wi-Fi unavailable; retrying. Dashboard will become OFFLINE.");
    configured = false;
    WiFi.reconnect();
    return;
  }
  if (!configured || millis() - lastConfig >= 10000) {
    lastConfig = millis();
    configured = fetchAssignments();
  }
  if (!configured) { Serial.println("Waiting for valid row/product assignments from backend."); return; }
  for (int i = 0; i < SENSOR_COUNT; ++i) {
    float distance = readDistance(i);
    delay(65); // Sequential pings and quiet time reduce cross-talk.
    if (distance < 0) { distance = readDistance(i); delay(65); }
    JsonDocument doc;
    doc["device_id"] = DEVICE_ID;
    doc["shelf_id"] = assigned[i].row;
    doc["sensor_id"] = SENSOR_IDS[i];
    doc["product_tag"] = assigned[i].tag;
    doc["sensor_type"] = "ultrasonic";
    doc["distance_cm"] = distance;
    String payload;
    serializeJson(doc, payload);
    WiFiClient transport;
    HTTPClient http;
    http.setConnectTimeout(1000);
    http.setTimeout(1500);
    if (http.begin(transport, BACKEND_URL)) {
      http.addHeader("Content-Type", "application/json");
      if (strlen(API_KEY)) http.addHeader("X-API-Key", API_KEY);
      int code = http.POST(payload);
      Serial.printf("%s %s %.2f cm -> HTTP %d\n", SENSOR_IDS[i], assigned[i].tag.c_str(), distance, code);
      if (code != 201) Serial.println(http.getString());
      http.end();
      if (code == 400) { configured = false; break; } // Refresh changed assignments.
    }
  }
}
