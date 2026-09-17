"""MQTT subscriber: bridges broker telemetry into the same processing
path used by POST /api/readings (Section 9/12 — MQTT is the primary
transport, HTTP is the fallback)."""

import json
import threading

import paho.mqtt.client as mqtt

from backend.services.monitoring import process_reading
from backend.services.alert_service import generate_alert

BROKER_HOST = "localhost"
BROKER_PORT = 1883
TOPIC = "storewatch/telemetry"


def _on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        processed = process_reading(payload)
        generate_alert(processed["shelf_id"], processed["status"])
    except (ValueError, TypeError, json.JSONDecodeError) as e:
        print(f"MQTT payload error: {e}")


def start_mqtt_listener():
    """Starts the MQTT subscriber in a background thread. Safe no-op
    (logs and returns) if the broker is unreachable."""
    client = mqtt.Client()
    client.on_message = _on_message

    def _run():
        try:
            client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
            client.subscribe(TOPIC)
            client.loop_forever()
        except OSError as e:
            print(f"MQTT broker unreachable ({e}); backend continues on HTTP only.")

    threading.Thread(target=_run, daemon=True).start()
