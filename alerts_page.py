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


def get_alert_trigger_description(alert_config: Dict[str, Any]) -> str:
    """Generate a human-readable description of what will trigger the alert."""
    ticker = alert_config.get("ticker", "N/A")
    alert_type = alert_config.get("type")

    if alert_type == "price":
        condition = alert_config.get("condition")
        target = alert_config.get("target_price", 0)

        condition_text = {
            "above": f"price goes ABOVE ${target:.2f}",
            "below": f"price goes BELOW ${target:.2f}",
            "crosses_above": f"price crosses ABOVE ${target:.2f}",
            "crosses_below": f"price crosses BELOW ${target:.2f}"
        }

        return f"{ticker} {condition_text.get(condition, 'meets condition')}"

    elif alert_type == "volume":
        multiplier = alert_config.get("multiplier", 2.0)
        return f"{ticker} volume exceeds {multiplier}x the 20-day average volume"

    elif alert_type == "pattern":
        pattern_type = alert_config.get("pattern_type", "Unknown")
        confidence = alert_config.get("min_confidence", 70)
        return f"{ticker} forms a '{pattern_type}' pattern with >{confidence}% confidence"

    elif alert_type == "news":
        sentiment = alert_config.get("sentiment", "any")
        if sentiment == "any":
            return f"{ticker} has significant news (any sentiment)"
        else:
            return f"{ticker} has {sentiment} news detected"

    elif alert_type == "indicator":
        indicator = alert_config.get("indicator", "RSI")
        condition = alert_config.get("condition", "above")
        threshold = alert_config.get("threshold", 0)

        condition_text = {
            "above": f"{indicator} goes ABOVE {threshold}",
            "below": f"{indicator} goes BELOW {threshold}",
            "crosses_above": f"{indicator} crosses ABOVE {threshold}",
            "crosses_below": f"{indicator} crosses BELOW {threshold}"
        }

        return f"{ticker} {condition_text.get(condition, 'meets condition')}"

    elif alert_type == "ema_cross":
        cross_type = alert_config.get("cross_type", "bullish")
        if cross_type == "bullish":
            return f"{ticker} EMA20 crosses ABOVE EMA50 (Golden Cross)"
        else:
            return f"{ticker} EMA20 crosses BELOW EMA50 (Death Cross)"

    elif alert_type == "macd_signal":
        cross_type = alert_config.get("cross_type", "bullish")
        if cross_type == "bullish":
            return f"{ticker} MACD crosses ABOVE signal line (Bullish)"
        else:
            return f"{ticker} MACD crosses BELOW signal line (Bearish)"

    return f"{ticker} meets alert conditions"


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
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Alerts", len(alerts))

    with col2:
        price_alerts = len([a for a in alerts if a.get("type") == "price"])
        st.metric("💰 Price", price_alerts)

    with col3:
        indicator_alerts = len([a for a in alerts if a.get("type") in ["indicator", "ema_cross", "macd_signal"]])
        st.metric("📉 Indicator", indicator_alerts)

    with col4:
        other_alerts = len([a for a in alerts if a.get("type") in ["pattern", "volume", "news"]])
        st.metric("📊 Other", other_alerts)
    
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
        "news": "#43e97b",
        "indicator": "#fa709a",
        "ema_cross": "#feca57",
        "macd_signal": "#48dbfb"
    }
    color = colors.get(alert_type, "#999")
    
    # Format details using the same helper function
    trigger_description = get_alert_trigger_description(alert)

    # Short version for card
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
            f"<p style='margin:8px 0 0 0;'><strong>🚨 Triggers when:</strong> {trigger_description}</p>"
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
            ["price", "volume", "pattern", "news", "indicator", "ema_cross", "macd_signal"],
            format_func=lambda x: {
                "price": "💰 Price Alert",
                "volume": "📊 Volume Alert",
                "pattern": "📈 Pattern Alert",
                "news": "📰 News Alert",
                "indicator": "📉 Indicator Alert (RSI, ATR, etc.)",
                "ema_cross": "🔀 EMA Crossover Alert",
                "macd_signal": "📊 MACD Signal Alert"
            }.get(x, x)
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

    elif alert_type == "indicator":
        st.markdown("### 📉 Indicator Alert Settings")
        st.caption("Get notified when a technical indicator crosses a threshold")

        col_a, col_b, col_c = st.columns(3)

        with col_a:
            indicator = st.selectbox(
                "Indicator",
                ["RSI14", "ATR14", "BandPos20", "Volume"],
                help="Select which indicator to monitor"
            )

        with col_b:
            condition = st.selectbox(
                "Condition",
                ["above", "below", "crosses_above", "crosses_below"],
                help="'crosses' detects when value moves from one side to the other"
            )

        with col_c:
            # Set default threshold based on indicator
            default_threshold = {
                "RSI14": 70.0 if "above" in condition else 30.0,
                "ATR14": 2.0,
                "BandPos20": 0.8 if "above" in condition else 0.2,
                "Volume": 1000000.0
            }.get(indicator, 50.0)

            threshold = st.number_input(
                "Threshold",
                min_value=0.0,
                value=default_threshold,
                step=0.1 if indicator in ["ATR14", "BandPos20"] else 1.0,
                help=f"Alert triggers when {indicator} {condition.replace('_', ' ')} this value"
            )

        # Show example
        st.info(f"**Example:** Alert when {ticker}'s {indicator} {condition.replace('_', ' ')} {threshold}")

        alert_config.update({
            "indicator": indicator,
            "condition": condition,
            "threshold": threshold
        })

    elif alert_type == "ema_cross":
        st.markdown("### 🔀 EMA Crossover Alert Settings")
        st.caption("Get notified when EMA20 crosses EMA50 (trend change signal)")

        cross_type = st.radio(
            "Crossover Type",
            ["bullish", "bearish"],
            format_func=lambda x: "🟢 Bullish (EMA20 crosses ABOVE EMA50 - Golden Cross)" if x == "bullish"
                                  else "🔴 Bearish (EMA20 crosses BELOW EMA50 - Death Cross)",
            help="Bullish = uptrend signal, Bearish = downtrend signal"
        )

        st.info(f"**Alert triggers when:** {ticker}'s EMA20 crosses {'above' if cross_type == 'bullish' else 'below'} EMA50")

        alert_config.update({
            "cross_type": cross_type
        })

    elif alert_type == "macd_signal":
        st.markdown("### 📊 MACD Signal Alert Settings")
        st.caption("Get notified when MACD crosses its signal line (momentum change)")

        cross_type = st.radio(
            "Signal Type",
            ["bullish", "bearish"],
            format_func=lambda x: "🟢 Bullish (MACD crosses ABOVE signal line)" if x == "bullish"
                                  else "🔴 Bearish (MACD crosses BELOW signal line)",
            help="Bullish = momentum turning up, Bearish = momentum turning down"
        )

        st.info(f"**Alert triggers when:** {ticker}'s MACD crosses {'above' if cross_type == 'bullish' else 'below'} its signal line")

        alert_config.update({
            "cross_type": cross_type
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
    
    # Show preview of what will trigger the alert
    st.markdown("### 🔍 Alert Preview")
    st.info(get_alert_trigger_description(alert_config))

    # Create button
    if st.button("✅ Create Alert", use_container_width=True, type="primary"):
        alert_id = create_alert(alert_config)

        # Build detailed trigger description
        trigger_desc = get_alert_trigger_description(alert_config)

        st.success(f"✅ Alert created successfully! ID: {alert_id}")

        # Show what will trigger it
        st.markdown("### 🚨 This alert will trigger when:")
        st.markdown(f"**{trigger_desc}**")

        # Send detailed notification email
        if email_notify and alert_config.get("email"):
            email_body = f"""Your {alert_type} alert for {ticker} is now active!

ALERT WILL TRIGGER WHEN:
{trigger_desc}

Alerts are checked automatically every 2 hours during market hours:
- 10:00 AM ET
- 12:00 PM ET
- 2:00 PM ET
- 4:15 PM ET (after market close)

You will receive an email notification when the alert triggers.
"""

            email_html = f"""
<html>
<body style="font-family: Arial, sans-serif; padding: 20px;">
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; border-radius: 10px; color: white;">
        <h2 style="margin: 0;">✅ Alert Created Successfully</h2>
        <h1 style="margin: 10px 0;">{ticker}</h1>
    </div>

    <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; margin-top: 20px;">
        <h3>🚨 This alert will trigger when:</h3>
        <p style="font-size: 16px; font-weight: bold; color: #667eea;">{trigger_desc}</p>
    </div>

    <div style="background: #fff3cd; padding: 15px; border-radius: 10px; margin-top: 20px;">
        <h4 style="margin: 0 0 10px 0;">📅 Alert Check Schedule:</h4>
        <ul style="margin: 0;">
            <li>10:00 AM ET - Mid-morning check</li>
            <li>12:00 PM ET - Noon check</li>
            <li>2:00 PM ET - Afternoon check</li>
            <li>4:15 PM ET - After market close</li>
        </ul>
        <p style="margin: 10px 0 0 0; font-size: 14px;">You will receive an email when the alert triggers.</p>
    </div>
</body>
</html>
"""

            send_email_alert(
                alert_config["email"],
                f"✅ SwingFinder Alert Created: {ticker}",
                email_body,
                email_html
            )

        st.info("💡 Alerts are checked every 2 hours during market hours (10 AM, 12 PM, 2 PM, 4:15 PM ET)")


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

