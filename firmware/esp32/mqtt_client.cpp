#include <WiFi.h>
#include <PubSubClient.h>
#include "mqtt_client.h"

// --- Fill these in, or better: load from a separate secrets header that
// is gitignored, so credentials never get committed. ---
static const char *WIFI_SSID = "YOUR_WIFI_SSID";
static const char *WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

static const char *MQTT_BROKER = "192.168.1.100"; // backend/broker host
static const int MQTT_PORT = 1883;
static const char *MQTT_TOPIC = "storewatch/telemetry";

WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);

static void connectWiFi() {
  if (WiFi.status() == WL_CONNECTED) return;

  Serial.printf("Connecting to Wi-Fi: %s\n", WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < 15000) {
    delay(300);
    Serial.print(".");
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("\nWi-Fi connected. IP: %s\n", WiFi.localIP().toString().c_str());
  } else {
    Serial.println("\nWi-Fi connection failed, will retry.");
  }
}

static void connectMQTT() {
  if (mqttClient.connected()) return;

  mqttClient.setServer(MQTT_BROKER, MQTT_PORT);

  String clientId = "ESP32Client-" + String((uint32_t)ESP.getEfuseMac(), HEX);
  if (mqttClient.connect(clientId.c_str())) {
    Serial.println("MQTT connected.");
  } else {
    Serial.printf("MQTT connect failed, rc=%d\n", mqttClient.state());
  }
}

void setupConnectivity() {
  connectWiFi();
  connectMQTT();
}

void ensureConnected() {
  connectWiFi();
  if (!mqttClient.connected()) {
    connectMQTT();
  }
  mqttClient.loop();
}

void publishReading(const char *deviceId, const char *shelfId,
                     const char *sensorType, float distanceCm) {
  if (!mqttClient.connected()) {
    Serial.println("MQTT not connected, skipping publish.");
    return;
  }

  // Minimal manual JSON construction to avoid pulling in ArduinoJson
  // for a scaffold. Swap for ArduinoJson if the payload grows.
  char payload[256];
  snprintf(payload, sizeof(payload),
           "{\"device_id\":\"%s\",\"shelf_id\":\"%s\","
           "\"sensor_type\":\"%s\",\"distance_cm\":%.2f,"
           "\"timestamp\":%lu}",
           deviceId, shelfId, sensorType, distanceCm, millis());

  mqttClient.publish(MQTT_TOPIC, payload);
  Serial.printf("Published: %s\n", payload);
}
