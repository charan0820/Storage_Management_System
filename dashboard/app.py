"""Optional Streamlit entry point. The live application now shares the Flask server."""
import os
import streamlit as st
st.set_page_config(page_title="StoreWatch", layout="centered")
st.title("StoreWatch")
st.write("The live shelf dashboard is served by the backend, with calibration and hardware status.")
st.link_button("Open live dashboard", os.environ.get("BACKEND_URL", "http://localhost:5000"))
st.code("python -m backend.app")
