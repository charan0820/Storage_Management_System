"""Data model + persistence helpers for sensor readings and alerts.

Interfaces defined here follow Section 13 of the project spec:
    save_reading(reading)
so backend/services code can stay agnostic of the SQL details.
"""

from dataclasses import dataclass, asdict
from typing import Optional

from backend.database.db import get_connection


@dataclass
class Reading:
    """A processed sensor reading, ready to persist.

    device_id / shelf_id / sensor_type / sensor_value come from the raw
    telemetry payload (Section 14). filtered_value and status are added
    by backend processing (services/monitoring.py).
    """
    device_id: str
    shelf_id: str
    sensor_type: str
    sensor_value: float
    filtered_value: float
    status: str
    timestamp: str


def save_reading(reading: Reading) -> int:
    """Persist a processed reading. Returns the new row id."""
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO sensor_readings
                (device_id, shelf_id, sensor_type, sensor_value,
                 filtered_value, status, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                reading.device_id,
                reading.shelf_id,
                reading.sensor_type,
                reading.sensor_value,
                reading.filtered_value,
                reading.status,
                reading.timestamp,
            ),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_latest_reading(shelf_id: str) -> Optional[dict]:
    """Return the most recent reading for a shelf, or None."""
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT * FROM sensor_readings
            WHERE shelf_id = ?
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            (shelf_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_all_latest_readings() -> list[dict]:
    """Return the most recent reading per shelf (used by the dashboard
    summary view)."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT sr.* FROM sensor_readings sr
            INNER JOIN (
                SELECT shelf_id, MAX(timestamp) AS max_ts
                FROM sensor_readings
                GROUP BY shelf_id
            ) latest
            ON sr.shelf_id = latest.shelf_id AND sr.timestamp = latest.max_ts
            """
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_history(shelf_id: str, limit: int = 200) -> list[dict]:
    """Return recent readings for a shelf, oldest first, for charting."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT * FROM sensor_readings
            WHERE shelf_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (shelf_id, limit),
        ).fetchall()
        return [dict(r) for r in rows][::-1]
    finally:
        conn.close()
