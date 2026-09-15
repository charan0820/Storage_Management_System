"""Routes for telemetry ingestion and reading queries."""

from flask import Blueprint, jsonify, request

from backend.services.monitoring import process_reading
from backend.services.alert_service import generate_alert
from backend.models.readings import (
    get_latest_reading,
    get_all_latest_readings,
    get_history,
)

sensor_bp = Blueprint("sensor_routes", __name__)


@sensor_bp.route("/api/readings", methods=["POST"])
def post_reading():
    """Ingest one telemetry payload from an ESP32 (or a simulator).

    Expected body (Section 14):
        {
          "device_id": "ESP32_01",
          "shelf_id": "SHELF_01",
          "sensor_type": "ultrasonic",
          "distance_cm": 8.4,
          "timestamp": "2026-09-14T18:30:00"   # optional
        }
    """
    payload = request.get_json(silent=True)
    if not payload:
        return jsonify({"error": "Invalid or missing JSON body"}), 400

    required = {"device_id", "shelf_id", "distance_cm"}
    missing = required - payload.keys()
    if missing:
        return jsonify({"error": f"Missing fields: {sorted(missing)}"}), 400

    try:
        processed = process_reading(payload)
    except (ValueError, TypeError) as e:
        return jsonify({"error": str(e)}), 400

    alert = generate_alert(processed["shelf_id"], processed["status"])
    processed["alert_generated"] = alert is not None

    return jsonify(processed), 201


@sensor_bp.route("/api/readings/<shelf_id>", methods=["GET"])
def get_shelf_reading(shelf_id):
    """Latest reading for a single shelf."""
    reading = get_latest_reading(shelf_id)
    if reading is None:
        return jsonify({"error": f"No readings found for {shelf_id}"}), 404
    return jsonify(reading)


@sensor_bp.route("/api/readings", methods=["GET"])
def get_all_readings():
    """Latest reading per shelf — powers the dashboard summary view."""
    return jsonify(get_all_latest_readings())


@sensor_bp.route("/api/readings/<shelf_id>/history", methods=["GET"])
def get_shelf_history(shelf_id):
    """Recent reading history for a shelf — powers historical charts."""
    limit = request.args.get("limit", default=200, type=int)
    return jsonify(get_history(shelf_id, limit=limit))
