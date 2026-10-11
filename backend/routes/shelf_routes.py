"""Product assignment, calibration and live shelf summary."""
from datetime import datetime, timezone
import math
from flask import Blueprint, jsonify, request
from backend.database.db import get_connection
from backend.models.readings import get_all_latest_readings
from backend.config import OFFLINE_SECONDS
from backend.services.monitoring import _recent_values, _lock

shelf_bp = Blueprint("shelves", __name__)

@shelf_bp.get("/api/shelves")
def shelves():
    conn = get_connection()
    try:
        rows = [dict(r) for r in conn.execute("SELECT * FROM shelves ORDER BY shelf_id")]
    finally:
        conn.close()
    latest = {r["shelf_id"]: r for r in get_all_latest_readings()}
    for shelf in rows:
        r = latest.get(shelf["shelf_id"])
        shelf.update(reading=r, status="WAITING", online=False, fill_percent=None)
        if r and shelf["updated_at"] and r["timestamp"] <= shelf["updated_at"]:
            shelf["reading"] = None
            continue
        if r:
            age = (datetime.now(timezone.utc) - datetime.fromisoformat(r["timestamp"])).total_seconds()
            shelf["online"] = 0 <= age <= OFFLINE_SECONDS
            shelf["status"] = r["status"] if shelf["online"] else "OFFLINE"
            if shelf["online"] and shelf["calibrated"] and r["sensor_value"] >= 0:
                shelf["fill_percent"] = round(max(0, min(100, 100 * (shelf["empty_cm"] - r["filtered_value"]) / (shelf["empty_cm"] - shelf["full_cm"]))), 1)
    return jsonify(rows)

@shelf_bp.put("/api/shelves/<shelf_id>")
def update_shelf(shelf_id):
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error="Expected a JSON object"), 400
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM shelves WHERE shelf_id=?", (shelf_id,)).fetchone()
        if not row:
            return jsonify(error="Unknown shelf"), 404
        values = dict(row)
        for key in ("product", "full_cm", "empty_cm", "low_percent"):
            if key in data:
                values[key] = data[key]
        try:
            if not isinstance(values["product"], str) or not 1 <= len(values["product"].strip()) <= 80:
                raise ValueError("Product must be 1..80 characters")
            for key in ("full_cm", "empty_cm", "low_percent"):
                values[key] = float(values[key])
                if not math.isfinite(values[key]):
                    raise ValueError("Calibration must be finite")
            if not 2 <= values["full_cm"] < values["empty_cm"] <= 400:
                raise ValueError("Require 2 <= full distance < empty distance <= 400 cm")
            if not 5 < values["low_percent"] < 90:
                raise ValueError("Low-stock threshold must be between 5 and 90 percent")
        except (TypeError, ValueError) as e:
            return jsonify(error=str(e)), 400
        calibrated = row["calibrated"] or {"full_cm", "empty_cm"}.issubset(data)
        conn.execute("UPDATE shelves SET product=?, full_cm=?, empty_cm=?, low_percent=?, calibrated=?, updated_at=? WHERE shelf_id=?",
                     (values["product"].strip(), values["full_cm"], values["empty_cm"], values["low_percent"], int(calibrated), datetime.now(timezone.utc).isoformat(), shelf_id))
        conn.commit()
        # Preserve history; the summary waits for a sample under new settings.
        with _lock:
            _recent_values.pop(shelf_id, None)
        return jsonify(ok=True, message="Saved. Waiting for a fresh reading.")
    finally:
        conn.close()
