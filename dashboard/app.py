"""StoreWatch Streamlit dashboard.

Run with:
    streamlit run dashboard/app.py

Reads exclusively from the backend API — never touches sensors or the
database directly (Section 34: dashboard should not read GPIO/DB directly).
"""

import requests
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

BACKEND_URL = "http://localhost:5000"

st.set_page_config(page_title="StoreWatch", layout="wide")
st.title("📦 StoreWatch — Live Shelf Monitoring")

REFRESH_SECONDS = 5
STATUS_EMOJI = {"FULL": "🟩", "LOW_STOCK": "🟧", "EMPTY": "🟥", "UNKNOWN": "⬜"}


@st.cache_data(ttl=REFRESH_SECONDS, show_spinner=False)
def fetch(path: str):
    try:
        resp = requests.get(f"{BACKEND_URL}{path}", timeout=5)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Could not reach backend at {BACKEND_URL}{path}: {e}")
        return None


# Each section is its own fragment: only that section's DOM updates on
# refresh, instead of the whole page re-rendering/flickering every cycle.

@st.fragment(run_every=f"{REFRESH_SECONDS}s")
def render_summary():
    readings = fetch("/api/readings") or []
    total = len(readings)
    low_stock = sum(1 for r in readings if r["status"] == "LOW_STOCK")
    empty = sum(1 for r in readings if r["status"] == "EMPTY")
    unknown = sum(1 for r in readings if r["status"] == "UNKNOWN")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Shelves monitored", total)
    col2.metric("Low stock", low_stock)
    col3.metric("Empty", empty)
    col4.metric("Unknown / offline", unknown)


@st.fragment(run_every=f"{REFRESH_SECONDS}s")
def render_shelf_status():
    st.subheader("Shelf Status")
    readings = fetch("/api/readings") or []
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


@st.fragment(run_every=f"{REFRESH_SECONDS}s")
def render_device_health():
    st.subheader("Device Health")
    devices = fetch("/api/devices") or []
    if devices:
        st.dataframe(pd.DataFrame(devices), use_container_width=True, hide_index=True)
    else:
        st.caption("No device data yet.")


@st.fragment(run_every=f"{REFRESH_SECONDS}s")
def render_alerts():
    st.subheader("⚠️ Active Alerts")
    alerts = fetch("/api/alerts") or []
    if alerts:
        for a in alerts:
            st.warning(f"**{a['shelf_id']}** — {a['message']}  \n_since {a['created_at']}_")
    else:
        st.success("No active alerts.")


@st.fragment(run_every=f"{REFRESH_SECONDS * 2}s")  # heaviest section: refresh less often
def render_history():
    st.subheader("Historical Sensor Readings")
    readings = fetch("/api/readings") or []
    if not readings:
        return
    shelf_options = sorted({r["shelf_id"] for r in readings})
    selected_shelf = st.selectbox("Shelf", shelf_options)
    history = fetch(f"/api/readings/{selected_shelf}/history?limit=50") or []
    if not history:
        st.caption("No history yet for this shelf.")
        return

    hist_df = pd.DataFrame(history)
    hist_df["timestamp"] = pd.to_datetime(hist_df["timestamp"], errors="coerce")

    # plotly + fixed uirevision: redraws data in place via JS instead of
    # Vega-Lite's full chart teardown/rebuild on every refresh cycle.
    value_fig = go.Figure(go.Scatter(x=hist_df["timestamp"], y=hist_df["filtered_value"], mode="lines"))
    value_fig.update_layout(height=300, margin=dict(l=0, r=0, t=10, b=0), uirevision="value_chart")
    st.plotly_chart(value_fig, use_container_width=True, key="value_chart")

    status_map = {"EMPTY": 0, "LOW_STOCK": 1, "FULL": 2, "UNKNOWN": -1}
    hist_df["status_level"] = hist_df["status"].map(status_map)
    st.caption("Status over time (2=FULL, 1=LOW_STOCK, 0=EMPTY, -1=UNKNOWN)")
    status_fig = go.Figure(go.Scatter(x=hist_df["timestamp"], y=hist_df["status_level"], mode="lines"))
    status_fig.update_layout(height=250, margin=dict(l=0, r=0, t=10, b=0), uirevision="status_chart")
    st.plotly_chart(status_fig, use_container_width=True, key="status_chart")


render_summary()
st.divider()
render_shelf_status()
st.divider()
render_device_health()
st.divider()
render_alerts()
st.divider()
render_history()
st.caption(f"Auto-refreshing (summary/status/alerts every {REFRESH_SECONDS}s, history every {REFRESH_SECONDS*2}s).")
