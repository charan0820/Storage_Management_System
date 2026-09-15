"""StoreWatch Streamlit dashboard.

Run with:
    streamlit run dashboard/app.py

Reads exclusively from the backend API — never touches sensors or the
database directly (Section 34: dashboard should not read GPIO/DB directly).
"""

import requests
import streamlit as st
import pandas as pd

BACKEND_URL = "http://localhost:5000"

st.set_page_config(page_title="StoreWatch", layout="wide")
st.title("📦 StoreWatch — Live Shelf Monitoring")


def fetch(path: str):
    try:
        resp = requests.get(f"{BACKEND_URL}{path}", timeout=5)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Could not reach backend at {BACKEND_URL}{path}: {e}")
        return None


readings = fetch("/api/readings") or []
alerts = fetch("/api/alerts") or []
devices = fetch("/api/devices") or []

# --- Summary row ---
total = len(readings)
low_stock = sum(1 for r in readings if r["status"] == "LOW_STOCK")
empty = sum(1 for r in readings if r["status"] == "EMPTY")
unknown = sum(1 for r in readings if r["status"] == "UNKNOWN")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Shelves monitored", total)
col2.metric("Low stock", low_stock)
col3.metric("Empty", empty)
col4.metric("Unknown / offline", unknown)

st.divider()

# --- Shelf status ---
st.subheader("Shelf Status")

STATUS_EMOJI = {
    "FULL": "🟩",
    "LOW_STOCK": "🟧",
    "EMPTY": "🟥",
    "UNKNOWN": "⬜",
}

if readings:
    df = pd.DataFrame(readings).sort_values("shelf_id")
    for _, row in df.iterrows():
        emoji = STATUS_EMOJI.get(row["status"], "⬜")
        c1, c2, c3, c4 = st.columns([2, 2, 2, 3])
        c1.write(f"**{row['shelf_id']}**")
        c2.write(f"{emoji} {row['status']}")
        c3.write(f"{row['filtered_value']:.1f} cm")
        c4.caption(f"Last update: {row['timestamp']}")
else:
    st.info("No readings yet. Start the backend and send telemetry, or load sample_readings.csv.")

st.divider()

# --- Device health ---
st.subheader("Device Health")
if devices:
    dev_df = pd.DataFrame(devices)
    st.dataframe(dev_df, use_container_width=True, hide_index=True)
else:
    st.caption("No device data yet.")

st.divider()

# --- Active alerts ---
st.subheader("⚠️ Active Alerts")
if alerts:
    for a in alerts:
        st.warning(f"**{a['shelf_id']}** — {a['message']}  \n_since {a['created_at']}_")
else:
    st.success("No active alerts.")

st.divider()

# --- Historical chart ---
st.subheader("Historical Sensor Readings")
if readings:
    shelf_options = sorted({r["shelf_id"] for r in readings})
    selected_shelf = st.selectbox("Shelf", shelf_options)
    history = fetch(f"/api/readings/{selected_shelf}/history") or []
    if history:
        hist_df = pd.DataFrame(history)
        hist_df["timestamp"] = pd.to_datetime(hist_df["timestamp"], errors="coerce")
        st.line_chart(hist_df.set_index("timestamp")[["filtered_value"]])
    else:
        st.caption("No history yet for this shelf.")

st.caption("Auto-refresh: rerun this page (Streamlit's rerun button) or wrap in st.rerun() + time.sleep() for polling.")
