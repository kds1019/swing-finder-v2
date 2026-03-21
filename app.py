# app.py
import streamlit as st
from scanner import scanner_ui
from analyzer import analyzer_ui
from active_trades import active_trades_ui
from alerts_page import show_alerts_page
from backtest_page import show_backtest_page
from journal_page import show_journal_page
from utils.mobile_styles import apply_mobile_styles, add_pwa_meta_tags
from utils.rate_limiter import show_rate_limit_status
from config import AppPage, init_session_state

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

# 🚀 MOBILE OPTIMIZATION: Session Keep-Alive
# Prevents session timeout when app is in background (e.g., when switching to Webull)
# This JavaScript pings the server every 30 seconds to keep the session alive
st.markdown("""
<script>
    // Keep session alive by pinging every 30 seconds
    setInterval(function() {
        // Send a small request to keep connection alive
        fetch(window.location.href, {method: 'HEAD'})
            .catch(err => console.log('Keep-alive ping failed:', err));
    }, 30000); // 30 seconds

    // Detect mobile device and store in session
    const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent) || window.innerWidth < 768;
    if (isMobile && window.parent) {
        window.parent.postMessage({type: 'streamlit:setComponentValue', value: {is_mobile: true}}, '*');
    }
</script>
""", unsafe_allow_html=True)

# Store mobile detection in session state
if "is_mobile" not in st.session_state:
    # Simple heuristic: check if user agent or screen width suggests mobile
    st.session_state["is_mobile"] = False  # Will be updated by JavaScript above

# ---------------- Optional: Simple Password Protection ----------------
# Uncomment this section if you want password protection instead of GitHub OAuth
# This works better on mobile and avoids GitHub 500 errors

# if "authenticated" not in st.session_state:
#     st.session_state.authenticated = False
#
# if not st.session_state.authenticated:
#     st.title("🔐 SwingFinder Login")
#     st.markdown("Enter password to access the app")
#
#     password = st.text_input("Password", type="password", key="login_password")
#
#     if st.button("Login", use_container_width=True):
#         # Get password from secrets or use default
#         correct_password = st.secrets.get("APP_PASSWORD", "swingfinder2024")
#
#         if password == correct_password:
#             st.session_state.authenticated = True
#             st.success("✅ Login successful!")
#             st.rerun()
#         else:
#             st.error("❌ Incorrect password")
#
#     st.stop()  # Stop here if not authenticated

# ---------------- Session Setup ----------------
# Initialize all session state variables with defaults
init_session_state()

# Normalize active page to ensure consistency
st.session_state["active_page"] = AppPage.normalize(st.session_state["active_page"])

# ---------------- Sidebar Navigation ----------------
st.sidebar.title("⚙️ SwingFinder Navigation")

# Define available pages
available_pages = [
    AppPage.PREMARKET.value,
    AppPage.SCANNER.value,
    AppPage.ANALYZER.value,
    AppPage.BACKTEST.value,
    AppPage.ALERTS.value,
    AppPage.ACTIVE_TRADES.value,
    AppPage.JOURNAL.value,
]

# Get current page index
try:
    current_index = available_pages.index(st.session_state["active_page"])
except ValueError:
    current_index = 0  # Default to Scanner if page not found

page = st.sidebar.radio(
    "Go to:",
    available_pages,
    index=current_index,
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
    # Clear the cache first so the new universe file is loaded
    st.cache_data.clear()
    refresh_universe_manual(TIINGO_TOKEN)
    st.rerun()  # Force a rerun to reload the universe

# ---------------- Rate Limit Status ----------------
st.sidebar.divider()
show_rate_limit_status()


# ---------------- Page Routing ----------------
if st.session_state["active_page"] == "Scanner":
    scanner_ui(TIINGO_TOKEN)
elif st.session_state["active_page"] == "Analyzer":
    analyzer_ui(TIINGO_TOKEN)
elif st.session_state["active_page"] == "Backtest":
    show_backtest_page(TIINGO_TOKEN)
elif st.session_state["active_page"] == "Alerts":
    show_alerts_page()
elif st.session_state["active_page"] == "Active Trades":
    active_trades_ui()
elif st.session_state["active_page"] == "Journal":
    show_journal_page()


