# app.py
import streamlit as st
from scanner import scanner_ui
from analyzer import analyzer_ui
from active_trades import active_trades_ui

import os
from dotenv import load_dotenv

# --- Load Tiingo token (works both locally and on Streamlit Cloud) ---
try:
    TIINGO_TOKEN = st.secrets["tiingo"]["api_key"]
except Exception:
    load_dotenv()
    TIINGO_TOKEN = os.getenv("TIINGO_TOKEN")

if not TIINGO_TOKEN:
    st.error("❌ Tiingo API token not found! Please set it in .env or Streamlit secrets.")

st.set_page_config(page_title="SwingFinder", layout="wide")

# ---------------- Session Setup ----------------
# Ensure consistent, properly capitalized page names
if "active_page" not in st.session_state:
    st.session_state["active_page"] = "Scanner"
else:
    page_val = st.session_state["active_page"].strip().lower()
    if page_val == "analyzer":
        st.session_state["active_page"] = "Analyzer"
    elif page_val == "scanner":
        st.session_state["active_page"] = "Scanner"
    elif page_val in ["active trades", "activetrades"]:
        st.session_state["active_page"] = "Active Trades"

# ---------------- Sidebar Navigation ----------------
st.sidebar.title("⚙️ SwingFinder Navigation")
page = st.sidebar.radio(
    "Go to:",
    ["Scanner", "Analyzer", "Active Trades"],
    index=["Scanner", "Analyzer", "Active Trades"].index(st.session_state["active_page"]),
)
st.session_state["active_page"] = page  # keep sidebar synced

# ---------------- Page Routing ----------------
if st.session_state["active_page"] == "Scanner":
    scanner_ui(TIINGO_TOKEN)
elif st.session_state["active_page"] == "Analyzer":
    analyzer_ui(TIINGO_TOKEN)
elif st.session_state["active_page"] == "Active Trades":
    active_trades_ui()


