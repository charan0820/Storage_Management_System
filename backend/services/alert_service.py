"""Alert generation with deduplication (Section 17/18 of the spec).

Rule: only generate a new alert on a transition INTO LOW_STOCK/EMPTY,
not on every reading. An alert is auto-resolved on transition back to
FULL (i.e. NORMAL).
"""

from datetime import datetime, timezone

from backend.database.db import get_connection

ALERTABLE_STATUSES = {"LOW_STOCK", "EMPTY"}


def generate_alert(shelf_id: str, status: str) -> dict | None:
    """Create an alert if this is a genuinely new problem state,
    resolve any open alert if the shelf has recovered.

    Returns the created alert dict, or None if no new alert was needed.
    """
    conn = get_connection()
    try:
        open_alert = conn.execute(
            """
            SELECT * FROM alerts
            WHERE shelf_id = ? AND resolved = 0
            ORDER BY created_at DESC LIMIT 1
            """,
            (shelf_id,),
        ).fetchone()

        if status in ALERTABLE_STATUSES:
            if open_alert is not None:
                # Already alerted and still unresolved -> no duplicate.
                return None

            message = _build_message(shelf_id, status)
            now = datetime.now(timezone.utc).isoformat()
            cur = conn.execute(
                """
                INSERT INTO alerts (shelf_id, alert_type, message, created_at, resolved)
                VALUES (?, ?, ?, ?, 0)
                """,
                (shelf_id, status, message, now),
            )
            conn.commit()
            return {
                "id": cur.lastrowid,
                "shelf_id": shelf_id,
                "alert_type": status,
                "message": message,
                "created_at": now,
                "resolved": 0,
            }

        else:
            # status is FULL/UNKNOWN -> resolve any open alert.
            if open_alert is not None:
                conn.execute(
                    "UPDATE alerts SET resolved = 1 WHERE id = ?",
                    (open_alert["id"],),
                )
                conn.commit()
            return None
    finally:
        conn.close()


def get_active_alerts() -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM alerts WHERE resolved = 0 ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def _build_message(shelf_id: str, status: str) -> str:
    if status == "EMPTY":
        return f"{shelf_id} is empty. Restock required."
    return f"{shelf_id} is running low. Restock recommended."
