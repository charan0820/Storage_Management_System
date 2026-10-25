"""SQLite connection handling and schema initialization for StoreWatch.

Schema matches Section 15 of the project spec:
  - sensor_readings: raw + filtered readings with computed status
  - alerts: generated alerts with resolution tracking
"""

import sqlite3
import os
import re
from pathlib import Path

DB_PATH = Path(os.environ.get("STOREWATCH_DB", str(Path(__file__).resolve().parent / "storewatch.db")))

SCHEMA = """
CREATE TABLE IF NOT EXISTS shelves (
    shelf_id TEXT PRIMARY KEY,
    product TEXT NOT NULL,
    device_id TEXT NOT NULL,
    full_cm REAL NOT NULL DEFAULT 5,
    empty_cm REAL NOT NULL DEFAULT 30,
    low_percent REAL NOT NULL DEFAULT 25,
    calibrated INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL DEFAULT ''
);

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
        # Add row metadata without discarding existing assignments or telemetry.
        columns = {r[1] for r in conn.execute('PRAGMA table_info(shelves)')}
        additions = {'parent_shelf': "TEXT NOT NULL DEFAULT 'RACK_01'",
                     'row_number': 'INTEGER NOT NULL DEFAULT 1',
                     'sensor_id': "TEXT NOT NULL DEFAULT ''",
                     'product_tag': "TEXT NOT NULL DEFAULT ''",
                     'length_cm': 'REAL NOT NULL DEFAULT 30',
                     'calibration_source': "TEXT NOT NULL DEFAULT 'measured'",
                     'active': 'INTEGER NOT NULL DEFAULT 1'}
        for name, definition in additions.items():
            if name not in columns:
                conn.execute(f'ALTER TABLE shelves ADD COLUMN {name} {definition}')
        from backend.config import CONFIG
        for shelf_id, shelf in CONFIG["shelves"].items():
            conn.execute("INSERT OR IGNORE INTO shelves (shelf_id, product, device_id, product_tag) VALUES (?, ?, ?, ?)",
                         (shelf_id, shelf["product"], shelf["device_id"], shelf['product_tag']))
            conn.execute('UPDATE shelves SET parent_shelf=?, row_number=?, sensor_id=?, active=1 WHERE shelf_id=?',
                         (shelf['parent_shelf'], shelf['row_number'], shelf['sensor_id'], shelf_id))
            existing = conn.execute('SELECT product, product_tag FROM shelves WHERE shelf_id=?', (shelf_id,)).fetchone()
            if not existing['product_tag']:
                tag = re.sub(r'[^A-Z0-9]+', '-', existing['product'].upper()).strip('-')[:50] or 'PRODUCT'
                conn.execute("UPDATE shelves SET product_tag=?, calibration_source='demo' WHERE shelf_id=?",
                             (f'{tag}-{shelf["row_number"]:03d}', shelf_id))
        # Retire the original third demo channel; retain all its history.
        conn.execute("UPDATE shelves SET active=0 WHERE shelf_id='SHELF_03'")
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
    print(f"Database initialized at {DB_PATH}")
