"""
Alert Management Page
Configure and test email alerts for your watchlist
"""

import streamlit as st
import os
from datetime import datetime
from utils.alerts import (
    send_premarket_alert, 
    send_breakout_alert, 
    send_daily_summary,
    get_alert_history
)
from utils.scanner import (
    check_premarket_gaps,
    check_breakouts,
    is_market_hours,
    is_premarket_hours,
    load_watchlist_with_entries
)
from utils.storage import load_json

# Page config
st.set_page_config(page_title="Alerts - SwingFinder", page_icon="🔔", layout="wide")

# Load Tiingo token
try:
    TIINGO_TOKEN = st.secrets.get("TIINGO_TOKEN") or st.secrets.get("TIINGO_API_KEY")
except:
    from dotenv import load_dotenv
    load_dotenv()
    TIINGO_TOKEN = os.getenv("TIINGO_TOKEN") or os.getenv("TIINGO_API_KEY")

if not TIINGO_TOKEN:
    st.error("❌ Tiingo API token not found!")
    st.stop()

# Header
st.title("🔔 Alert System")
st.markdown("**Monitor your watchlist and get email alerts when opportunities arise**")

# Check email configuration
email_configured = bool(st.secrets.get("ALERT_EMAIL") and st.secrets.get("USER_EMAIL"))

if not email_configured:
    st.error("❌ Email not configured! Please add ALERT_EMAIL and USER_EMAIL to secrets.toml")
    st.stop()

st.success(f"✅ Email alerts configured: {st.secrets.get('USER_EMAIL')}")

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "🧪 Test Alerts", "📜 Alert History", "⚙️ Settings"])

# ============================================================================
# TAB 1: Dashboard
# ============================================================================
with tab1:
    st.header("Alert Dashboard")
    
    # Current status
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if is_premarket_hours():
            st.info("🌅 **Pre-Market Hours**\nMonitoring for gaps")
        elif is_market_hours():
            st.success("📈 **Market Hours**\nMonitoring for breakouts")
        else:
            st.warning("🌙 **After Hours**\nMarket closed")
    
    with col2:
        watchlist = load_watchlist_with_entries()
        st.metric("Watchlist Stocks", len(watchlist))
    
    with col3:
        # Count stocks with entry points set
        with_entries = sum(1 for item in watchlist if isinstance(item, dict) and item.get('entry'))
        st.metric("With Entry Points", with_entries)
    
    st.divider()
    
    # Manual scan buttons
    st.subheader("Manual Scans")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🌅 Scan for Pre-Market Gaps", use_container_width=True):
            with st.spinner("Scanning watchlist..."):
                gaps = check_premarket_gaps(TIINGO_TOKEN, gap_threshold=2.0)
                
                if gaps:
                    st.success(f"Found {len(gaps)} stocks with significant gaps!")
                    
                    for gap in gaps:
                        with st.expander(f"{gap['symbol']} - {gap['change_pct']:+.2f}%"):
                            st.write(f"**Current:** ${gap['current_price']:.2f}")
                            st.write(f"**Previous Close:** ${gap['prev_close']:.2f}")
                            st.write(f"**Change:** {gap['change_pct']:+.2f}%")
                            
                            if gap.get('setup_type'):
                                st.write(f"**Your Setup:** {gap['setup_type']}")
                            if gap.get('entry'):
                                st.write(f"**Entry Point:** ${gap['entry']:.2f}")
                else:
                    st.info("No significant gaps found (threshold: 2%)")
    
    with col2:
        if st.button("🚨 Scan for Breakouts", use_container_width=True):
            with st.spinner("Scanning watchlist..."):
                breakouts = check_breakouts(TIINGO_TOKEN)
                
                if breakouts:
                    st.success(f"Found {len(breakouts)} breakouts!")
                    
                    for bo in breakouts:
                        with st.expander(f"{bo['symbol']} - Entry Triggered!"):
                            st.write(f"**Current Price:** ${bo['current_price']:.2f}")
                            st.write(f"**Entry:** ${bo['entry_price']:.2f} ✅")
                            st.write(f"**Setup:** {bo['setup_type']}")
                            if bo.get('stop'):
                                st.write(f"**Stop:** ${bo['stop']:.2f}")
                            if bo.get('target'):
                                st.write(f"**Target:** ${bo['target']:.2f}")
                            if bo.get('volume_ratio'):
                                st.write(f"**Volume:** {bo['volume_ratio']:.1f}x average")
                else:
                    st.info("No breakouts detected")

# ============================================================================
# TAB 2: Test Alerts
# ============================================================================
with tab2:
    st.header("🧪 Test Email Alerts")
    st.markdown("Send test emails to make sure everything is working")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Pre-Market Alert Test")
        if st.button("📧 Send Test Pre-Market Alert", use_container_width=True):
            success = send_premarket_alert(
                symbol="TEST",
                current_price=105.50,
                prev_close=100.00,
                change_pct=5.5,
                setup_type="Bull Flag (Test)",
                entry=106.00
            )
            
            if success:
                st.success("✅ Test pre-market alert sent! Check your email.")
            else:
                st.error("❌ Failed to send alert. Check email configuration.")
    
    with col2:
        st.subheader("Breakout Alert Test")
        if st.button("📧 Send Test Breakout Alert", use_container_width=True):
            success = send_breakout_alert(
                symbol="TEST",
                current_price=106.50,
                entry_price=106.00,
                setup_type="Bull Flag (Test)",
                stop=103.00,
                target=112.00,
                volume_ratio=2.5,
                notes="This is a test alert"
            )
            
            if success:
                st.success("✅ Test breakout alert sent! Check your email.")
            else:
                st.error("❌ Failed to send alert. Check email configuration.")

# ============================================================================
# TAB 3: Alert History
# ============================================================================
with tab3:
    st.header("📜 Alert History")
    
    history = get_alert_history(limit=50)
    
    if history:
        st.markdown(f"**Last {len(history)} alerts**")
        
        for entry in reversed(history):  # Show newest first
            timestamp = entry.get('triggered_at', 'Unknown')
            ticker = entry.get('ticker', 'N/A')
            message = entry.get('message', 'No message')
            
            st.markdown(f"**{timestamp}** - {ticker}: {message}")
    else:
        st.info("No alert history yet")

# ============================================================================
# TAB 4: Settings
# ============================================================================
with tab4:
    st.header("⚙️ Alert Settings")
    
    st.subheader("Email Configuration")
    st.code(f"""
Alert Email: {st.secrets.get('ALERT_EMAIL', 'Not configured')}
User Email: {st.secrets.get('USER_EMAIL', 'Not configured')}
Status: {'✅ Configured' if email_configured else '❌ Not configured'}
""")
    
    st.subheader("Alert Thresholds")
    st.markdown("""
**Pre-Market Gap Threshold:** 2.0%  
**Volume Spike Threshold:** 2.0x average  
**Scan Frequency:** Every 5 minutes (during market hours)
""")
    
    st.info("💡 **Tip:** To change these settings, modify the scanner.py file")

