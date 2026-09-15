"""Basic monitoring analytics (Section 21/26 of the spec).

Kept separate from backend/ so it can be run standalone (e.g. as a
scheduled job or notebook) against the same SQLite database.
"""

from collections import Counter
from datetime import datetime

from backend.database.db import get_connection


def shelf_status_distribution(shelf_id: str) -> dict:
    """Count how many readings fell into each status for a shelf —
    a quick view of how much time a shelf spends FULL vs LOW vs EMPTY."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT status FROM sensor_readings WHERE shelf_id = ?",
            (shelf_id,),
        ).fetchall()
        return dict(Counter(r["status"] for r in rows))
    finally:
        conn.close()


def average_reading_interval_seconds(shelf_id: str) -> float | None:
    """Rough measure of sensor update interval (Section 26)."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT timestamp FROM sensor_readings
            WHERE shelf_id = ? ORDER BY timestamp ASC
            """,
            (shelf_id,),
        ).fetchall()
        timestamps = []
        for r in rows:
            try:
                timestamps.append(datetime.fromisoformat(r["timestamp"]))
            except ValueError:
                continue
        if len(timestamps) < 2:
            return None
        deltas = [
            (timestamps[i + 1] - timestamps[i]).total_seconds()
            for i in range(len(timestamps) - 1)
        ]
        return sum(deltas) / len(deltas)
    finally:
        conn.close()


def alert_counts() -> dict:
    """Total and currently-active alert counts, overall."""
    conn = get_connection()
    try:
        total = conn.execute("SELECT COUNT(*) AS c FROM alerts").fetchone()["c"]
        active = conn.execute(
            "SELECT COUNT(*) AS c FROM alerts WHERE resolved = 0"
        ).fetchone()["c"]
        return {"total": total, "active": active, "resolved": total - active}
    finally:
        conn.close()
