"""
Alert Management Page
Create, manage, and monitor alerts for watchlist stocks
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any
from utils.alerts import (
    create_alert, get_active_alerts, deactivate_alert, delete_alert,
    get_alert_history, send_email_alert
)
from utils.storage import load_json, load_watchlist


def show_alerts_page():
    """Main alerts management page."""
    
    st.title("🔔 Alert Management")
    st.markdown("**Create and manage alerts for your watchlist stocks**")
    
    # Tabs
    tab1, tab2, tab3 = st.tabs(["📋 Active Alerts", "➕ Create Alert", "📊 Alert History"])
    
    with tab1:
        show_active_alerts()
    
    with tab2:
        show_create_alert()
    
    with tab3:
        show_alert_history()


def show_active_alerts():
    """Display active alerts."""
    
    st.subheader("Active Alerts")
    
    alerts = get_active_alerts()
    
    if not alerts:
        st.info("No active alerts. Create one in the 'Create Alert' tab!")
        return
    
    # Summary
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Alerts", len(alerts))
    
    with col2:
        price_alerts = len([a for a in alerts if a.get("type") == "price"])
        st.metric("Price Alerts", price_alerts)
    
    with col3:
        pattern_alerts = len([a for a in alerts if a.get("type") == "pattern"])
        st.metric("Pattern Alerts", pattern_alerts)
    
    st.divider()
    
    # Display alerts
    for alert in alerts:
        display_alert_card(alert)


def display_alert_card(alert: Dict[str, Any]):
    """Display a single alert as a card."""
    
    ticker = alert.get("ticker", "N/A")
    alert_type = alert.get("type", "unknown")
    alert_id = alert.get("id")
    
    # Color based on type
    colors = {
        "price": "#667eea",
        "volume": "#f093fb",
        "pattern": "#4facfe",
        "news": "#43e97b"
    }
    color = colors.get(alert_type, "#999")
    
    # Format details
    if alert_type == "price":
        condition = alert.get("condition")
        target = alert.get("target_price")
        details = f"{condition.title()} ${target:.2f}"
    elif alert_type == "volume":
        multiplier = alert.get("multiplier")
        details = f"Volume > {multiplier}x average"
    elif alert_type == "pattern":
        pattern_type = alert.get("pattern_type")
        confidence = alert.get("min_confidence", 70)
        details = f"{pattern_type} (>{confidence}% confidence)"
    elif alert_type == "news":
        sentiment = alert.get("sentiment")
        details = f"{sentiment.title()} news"
    else:
        details = "Custom alert"
    
    # Notification methods
    notify_methods = []
    if alert.get("email_notify"):
        notify_methods.append("📧 Email")
    if alert.get("sms_notify"):
        notify_methods.append("📱 SMS")
    notify_str = " + ".join(notify_methods) if notify_methods else "No notifications"
    
    # Display card
    col_main, col_actions = st.columns([4, 1])
    
    with col_main:
        st.markdown(
            f"<div style='background:{color};padding:16px;border-radius:10px;color:white;margin:8px 0;'>"
            f"<h3 style='margin:0;'>{ticker} - {alert_type.title()} Alert</h3>"
            f"<p style='margin:8px 0 0 0;'>{details}</p>"
            f"<p style='margin:4px 0 0 0;font-size:12px;'>{notify_str}</p>"
            f"</div>",
            unsafe_allow_html=True
        )
    
    with col_actions:
        if st.button("🗑️", key=f"delete_{alert_id}", help="Delete alert"):
            delete_alert(alert_id)
            st.rerun()
        
        if st.button("⏸️", key=f"pause_{alert_id}", help="Pause alert"):
            deactivate_alert(alert_id)
            st.rerun()


def show_create_alert():
    """Create new alert form."""

    st.subheader("Create New Alert")

    # Check if Scanner has multiple watchlists
    all_watchlists = {}
    selected_watchlist_name = None

    if hasattr(st, 'session_state') and 'watchlists' in st.session_state:
        all_watchlists = st.session_state.watchlists

        if all_watchlists:
            # Let user choose which watchlist
            st.markdown("### 📁 Select Watchlist")
            selected_watchlist_name = st.selectbox(
                "Choose watchlist to create alerts from:",
                options=list(all_watchlists.keys()),
                index=0
            )
            watchlist = all_watchlists.get(selected_watchlist_name, [])
        else:
            watchlist = load_watchlist()
    else:
        # Fallback to load_watchlist
        watchlist = load_watchlist()

    if not watchlist:
        st.warning("⚠️ Your watchlist is empty! Add stocks in Scanner first.")
        st.info("👈 Go to Scanner → Watchlist Management → Add stocks")
        return
    
    # Alert configuration
    col1, col2 = st.columns(2)
    
    with col1:
        ticker = st.selectbox("Select Stock", watchlist)
        alert_type = st.selectbox(
            "Alert Type",
            ["price", "volume", "pattern", "news"]
        )
    
    with col2:
        email_notify = st.checkbox("📧 Email Notification", value=True)
        sms_notify = st.checkbox("📱 SMS Notification", value=False)
    
    st.divider()
    
    # Type-specific settings
    alert_config = {"ticker": ticker, "type": alert_type}
    
    if alert_type == "price":
        st.markdown("### Price Alert Settings")
        
        col_a, col_b = st.columns(2)
        
        with col_a:
            condition = st.selectbox(
                "Condition",
                ["above", "below", "crosses_above", "crosses_below"]
            )
        
        with col_b:
            target_price = st.number_input("Target Price ($)", min_value=0.01, value=100.0, step=0.01)
        
        alert_config.update({
            "condition": condition,
            "target_price": target_price
        })
    
    elif alert_type == "volume":
        st.markdown("### Volume Alert Settings")
        
        multiplier = st.slider("Volume Multiplier", 1.5, 5.0, 2.0, 0.5)
        
        alert_config.update({
            "multiplier": multiplier
        })
    
    elif alert_type == "pattern":
        st.markdown("### Pattern Alert Settings")
        
        col_a, col_b = st.columns(2)
        
        with col_a:
            pattern_type = st.selectbox(
                "Pattern Type",
                ["Bull Flag", "Cup and Handle", "Double Bottom", "Ascending Triangle"]
            )
        
        with col_b:
            min_confidence = st.slider("Min Confidence (%)", 50, 100, 70, 5)
        
        alert_config.update({
            "pattern_type": pattern_type,
            "min_confidence": min_confidence
        })
    
    elif alert_type == "news":
        st.markdown("### News Alert Settings")
        
        sentiment = st.selectbox(
            "Sentiment",
            ["bullish", "bearish", "any"]
        )
        
        alert_config.update({
            "sentiment": sentiment
        })
    
    # Notification settings
    alert_config.update({
        "email_notify": email_notify,
        "sms_notify": sms_notify
    })
    
    if email_notify:
        email = st.text_input("Email Address", value=st.secrets.get("USER_EMAIL", ""))
        alert_config["email"] = email
    
    if sms_notify:
        phone = st.text_input("Phone Number", value=st.secrets.get("USER_PHONE", ""), help="Format: +1234567890")
        alert_config["phone"] = phone
    
    st.divider()
    
    # Create button
    if st.button("✅ Create Alert", use_container_width=True, type="primary"):
        alert_id = create_alert(alert_config)
        st.success(f"✅ Alert created successfully! ID: {alert_id}")
        
        # Send test notification
        if email_notify and alert_config.get("email"):
            send_email_alert(
                alert_config["email"],
                f"SwingFinder Alert Created: {ticker}",
                f"Your {alert_type} alert for {ticker} is now active!",
                f"<h2>Alert Created</h2><p>Your {alert_type} alert for {ticker} is now active!</p>"
            )
        
        st.info("💡 Tip: Alerts are checked every 5 minutes when the app is running")


def show_alert_history():
    """Display alert trigger history."""
    
    st.subheader("Alert History")
    
    history = get_alert_history(limit=50)
    
    if not history:
        st.info("No alerts have been triggered yet")
        return
    
    # Convert to DataFrame
    df = pd.DataFrame(history)
    
    # Format
    df["triggered_at"] = pd.to_datetime(df["triggered_at"]).dt.strftime("%Y-%m-%d %H:%M:%S")
    
    # Display
    st.dataframe(
        df[["ticker", "message", "triggered_at"]],
        use_container_width=True,
        height=400
    )
    
    # Stats
    st.divider()
    st.subheader("📊 Statistics")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Triggers", len(history))
    
    with col2:
        unique_tickers = df["ticker"].nunique()
        st.metric("Unique Tickers", unique_tickers)
    
    with col3:
        if len(history) > 0:
            most_common = df["ticker"].value_counts().index[0]
            st.metric("Most Active", most_common)


if __name__ == "__main__":
    show_alerts_page()

