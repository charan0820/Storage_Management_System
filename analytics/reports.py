"""Generate a plain-text summary report from stored readings/alerts.

Run with:
    python analytics/reports.py
"""

from backend.database.db import get_connection
from analytics.statistics import (
    shelf_status_distribution,
    average_reading_interval_seconds,
    alert_counts,
)


def generate_report() -> str:
    conn = get_connection()
    try:
        shelves = [
            r["shelf_id"]
            for r in conn.execute(
                "SELECT DISTINCT shelf_id FROM sensor_readings"
            ).fetchall()
        ]
    finally:
        conn.close()

    lines = ["StoreWatch — Monitoring Report", "=" * 32, ""]

    if not shelves:
        lines.append("No data collected yet.")
        return "\n".join(lines)

    for shelf_id in sorted(shelves):
        lines.append(f"Shelf: {shelf_id}")
        dist = shelf_status_distribution(shelf_id)
        for status, count in sorted(dist.items()):
            lines.append(f"  {status}: {count} readings")
        interval = average_reading_interval_seconds(shelf_id)
        if interval is not None:
            lines.append(f"  Avg update interval: {interval:.1f}s")
        lines.append("")

    counts = alert_counts()
    lines.append("Alerts")
    lines.append(f"  Total: {counts['total']}")
    lines.append(f"  Active: {counts['active']}")
    lines.append(f"  Resolved: {counts['resolved']}")

    return "\n".join(lines)


if __name__ == "__main__":
    print(generate_report())
