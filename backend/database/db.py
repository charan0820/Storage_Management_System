"""SQLite connection handling and schema initialization for StoreWatch.

Schema matches Section 15 of the project spec:
  - sensor_readings: raw + filtered readings with computed status
  - alerts: generated alerts with resolution tracking
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "storewatch.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS sensor_readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL,
    shelf_id TEXT NOT NULL,
    sensor_type TEXT NOT NULL,
    sensor_value REAL,
    filtered_value REAL,
    status TEXT NOT NULL,
    timestamp TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    shelf_id TEXT NOT NULL,
    alert_type TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL,
    resolved INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_readings_shelf_time
    ON sensor_readings (shelf_id, timestamp);

CREATE INDEX IF NOT EXISTS idx_alerts_shelf_resolved
    ON alerts (shelf_id, resolved);
"""


def get_connection():
    """Return a new SQLite connection with row access by column name."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't already exist. Safe to call on every
    backend startup."""
    conn = get_connection()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
    print(f"Database initialized at {DB_PATH}")
