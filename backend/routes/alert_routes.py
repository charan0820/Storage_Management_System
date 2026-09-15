"""Routes for alert queries and manual resolution."""

from flask import Blueprint, jsonify

from backend.database.db import get_connection
from backend.services.alert_service import get_active_alerts

alert_bp = Blueprint("alert_routes", __name__)


@alert_bp.route("/api/alerts", methods=["GET"])
def list_active_alerts():
    return jsonify(get_active_alerts())


@alert_bp.route("/api/alerts/<int:alert_id>/resolve", methods=["POST"])
def resolve_alert(alert_id):
    """Manually resolve an alert (e.g. staff confirms restock happened)."""
    conn = get_connection()
    try:
        cur = conn.execute(
            "UPDATE alerts SET resolved = 1 WHERE id = ?", (alert_id,)
        )
        conn.commit()
        if cur.rowcount == 0:
            return jsonify({"error": f"Alert {alert_id} not found"}), 404
        return jsonify({"id": alert_id, "resolved": True})
    finally:
        conn.close()
