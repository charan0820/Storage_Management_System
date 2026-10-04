"""StoreWatch backend entry point.

Run with:
    python backend/app.py

This is the source of truth for shelf status (Section 34) — the ESP32
only reports sensor data, and the dashboard only reads from this API.
"""

from datetime import datetime, timezone

from flask import Flask, jsonify
from flask_cors import CORS

from backend.database.db import init_db
from backend.routes.sensor_routes import sensor_bp
from backend.routes.alert_routes import alert_bp
from backend.models.readings import get_all_latest_readings

# Device considered OFFLINE if no reading received within this window.
# Keep in sync with config.yaml -> device_health.offline_after_seconds.
OFFLINE_AFTER_SECONDS = 60


def create_app() -> Flask:
    app = Flask(__name__)
    CORS(app)

    init_db()

    app.register_blueprint(sensor_bp)
    app.register_blueprint(alert_bp)

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok", "service": "storewatch-backend"})

    @app.route("/api/devices", methods=["GET"])
    def device_status():
        """Basic device health (Section 22): ONLINE/OFFLINE per shelf,
        derived from how recently each shelf's latest reading arrived.
        """
        readings = get_all_latest_readings()
        now = datetime.now(timezone.utc)
        devices = []
        for r in readings:
            age_seconds = _age_seconds(r["timestamp"], now)
            devices.append({
                "device_id": r["device_id"],
                "shelf_id": r["shelf_id"],
                "last_seen": r["timestamp"],
                "status": "OFFLINE" if age_seconds is None or age_seconds > OFFLINE_AFTER_SECONDS else "ONLINE",
            })
        return jsonify(devices)

    return app


def _age_seconds(timestamp_str: str, now: datetime):
    try:
        ts = datetime.fromisoformat(timestamp_str)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return (now - ts).total_seconds()
    except (ValueError, TypeError):
        return None


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
