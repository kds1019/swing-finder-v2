# app.py
import streamlit as st
from scanner import scanner_ui
from analyzer import analyzer_ui
from active_trades import active_trades_ui
from fundamentals_scanner import show_fundamentals_scanner
from news_feed import show_news_feed
from strength_screener import show_strength_screener
from alerts_page import show_alerts_page
from utils.mobile_styles import apply_mobile_styles, add_pwa_meta_tags

import os
import json
from datetime import datetime
from dotenv import load_dotenv

# --- Load Tiingo token (works both locally and on Streamlit Cloud) ---
try:
    # Try flat structure first (matches secrets.toml)
    TIINGO_TOKEN = st.secrets.get("TIINGO_TOKEN") or st.secrets.get("TIINGO_API_KEY")
except Exception:
    TIINGO_TOKEN = None

# Fallback to .env file
if not TIINGO_TOKEN:
    load_dotenv()
    TIINGO_TOKEN = os.getenv("TIINGO_TOKEN") or os.getenv("TIINGO_API_KEY")

if not TIINGO_TOKEN:
    st.error("❌ Tiingo API token not found! Please set it in .env or Streamlit secrets.")
    st.stop()

st.set_page_config(
    page_title="SwingFinder",
    layout="wide",
    initial_sidebar_state="auto",  # Auto-collapse on mobile
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': "# SwingFinder 🚀\nProfessional Swing Trading Platform"
    }
)

# Apply mobile-responsive styles
apply_mobile_styles()
add_pwa_meta_tags()

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
    elif page_val in ["fundamentals", "fundamentals scanner"]:
        st.session_state["active_page"] = "Fundamentals"
    elif page_val in ["news", "news feed"]:
        st.session_state["active_page"] = "News"
    elif page_val in ["strength", "relative strength"]:
        st.session_state["active_page"] = "Strength"
    elif page_val in ["alerts", "alert management"]:
        st.session_state["active_page"] = "Alerts"

# ---------------- Sidebar Navigation ----------------
st.sidebar.title("⚙️ SwingFinder Navigation")

page = st.sidebar.radio(
    "Go to:",
    ["Scanner", "Fundamentals", "News", "Strength", "Analyzer", "Active Trades", "Alerts"],
    index=["Scanner", "Fundamentals", "News", "Strength", "Analyzer", "Active Trades", "Alerts"].index(st.session_state["active_page"]),
)
st.session_state["active_page"] = page  # keep sidebar synced

# ---------------- Manual Universe Refresh ----------------
from utils.universe_builder import refresh_universe_manual, CACHE_PATH

st.sidebar.divider()
st.sidebar.subheader("🧭 Universe Tools")

# Show last update timestamp if available
if os.path.exists(CACHE_PATH):
    try:
        with open(CACHE_PATH, "r") as f:
            data = json.load(f)
        last_updated = data.get("meta", {}).get("last_updated", "Unknown")
    except Exception:
        last_updated = "Unknown"
else:
    last_updated = "Not yet created"

st.sidebar.markdown(f"**Last Updated:** {last_updated}")

if st.sidebar.button("🔄 Refresh Tiingo Universe"):
    refresh_universe_manual(TIINGO_TOKEN)


# ---------------- Page Routing ----------------
if st.session_state["active_page"] == "Scanner":
    scanner_ui(TIINGO_TOKEN)
elif st.session_state["active_page"] == "Fundamentals":
    show_fundamentals_scanner()
elif st.session_state["active_page"] == "News":
    show_news_feed()
elif st.session_state["active_page"] == "Strength":
    show_strength_screener()
elif st.session_state["active_page"] == "Analyzer":
    analyzer_ui(TIINGO_TOKEN)
elif st.session_state["active_page"] == "Active Trades":
    active_trades_ui()
elif st.session_state["active_page"] == "Alerts":
    show_alerts_page()


