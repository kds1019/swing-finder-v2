"""
Alert System for SwingFinder
Email and SMS notifications for watchlist signals
"""

import smtplib
import streamlit as st
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import os
from utils.storage import load_json, save_json, load_gist_json, save_gist_json


def _get_alerts_gist_id() -> Optional[str]:
    """Get Gist ID for alerts cloud persistence."""
    return (
        st.secrets.get("GIST_ALERTS_ID")
        or st.secrets.get("GIST_ID")  # Use existing Gist ID
        or os.getenv("GIST_ALERTS_ID")
        or os.getenv("GIST_ID")
    )


def send_email_alert(to_email: str, subject: str, body: str, html_body: str = None) -> bool:
    """
    Send email alert using Gmail SMTP.
    Requires Gmail app password in secrets.
    """
    try:
        # Get email credentials from secrets
        from_email = st.secrets.get("ALERT_EMAIL", "")
        app_password = st.secrets.get("ALERT_EMAIL_PASSWORD", "")
        
        if not from_email or not app_password:
            return False
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Add plain text and HTML parts
        part1 = MIMEText(body, 'plain')
        msg.attach(part1)
        
        if html_body:
            part2 = MIMEText(html_body, 'html')
            msg.attach(part2)
        
        # Send via Gmail SMTP
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(from_email, app_password)
            server.send_message(msg)
        
        return True
        
    except Exception as e:
        st.error(f"Failed to send email: {e}")
        return False


def send_sms_alert(phone_number: str, message: str) -> bool:
    """
    Send SMS alert using Twilio.
    Requires Twilio credentials in secrets.
    """
    try:
        from twilio.rest import Client
        
        # Get Twilio credentials
        account_sid = st.secrets.get("TWILIO_ACCOUNT_SID", "")
        auth_token = st.secrets.get("TWILIO_AUTH_TOKEN", "")
        from_number = st.secrets.get("TWILIO_PHONE_NUMBER", "")
        
        if not account_sid or not auth_token or not from_number:
            return False
        
        # Send SMS
        client = Client(account_sid, auth_token)
        message = client.messages.create(
            body=message,
            from_=from_number,
            to=phone_number
        )
        
        return True
        
    except Exception as e:
        st.error(f"Failed to send SMS: {e}")
        return False


def _load_alerts() -> List[Dict[str, Any]]:
    """Load alerts from cloud (Gist) or local file."""
    gist_id = _get_alerts_gist_id()

    # Try loading from Gist first (for Streamlit Cloud persistence)
    if gist_id:
        try:
            data = load_gist_json(gist_id, "alerts.json")
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and "alerts" in data:
                return data["alerts"] if isinstance(data["alerts"], list) else []
        except Exception:
            pass  # Fall back to local

    # Fallback to local file
    alerts = load_json("data/alerts.json", default=[])
    return alerts if isinstance(alerts, list) else []


def _save_alerts(alerts: List[Dict[str, Any]]) -> None:
    """Save alerts to both cloud (Gist) and local file."""
    # Save to local file
    save_json(alerts, "data/alerts.json")

    # Save to Gist for cloud persistence
    gist_id = _get_alerts_gist_id()
    if gist_id:
        try:
            save_gist_json(gist_id, "alerts.json", alerts)
        except Exception as e:
            # Don't fail if cloud save fails, local is still saved
            pass


def create_alert(alert_config: Dict[str, Any]) -> str:
    """
    Create a new alert and save to cloud + local storage.
    Returns alert ID.
    """
    alerts = _load_alerts()

    # Generate alert ID
    alert_id = f"alert_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    alert = {
        "id": alert_id,
        "created_at": datetime.now().isoformat(),
        "active": True,
        **alert_config
    }

    alerts.append(alert)
    _save_alerts(alerts)

    return alert_id


def get_active_alerts() -> List[Dict[str, Any]]:
    """Get all active alerts from cloud or local storage."""
    alerts = _load_alerts()
    return [a for a in alerts if a.get("active", False)]


def deactivate_alert(alert_id: str):
    """Deactivate an alert in cloud + local storage."""
    alerts = _load_alerts()

    for alert in alerts:
        if alert["id"] == alert_id:
            alert["active"] = False

    _save_alerts(alerts)


def delete_alert(alert_id: str):
    """Delete an alert from cloud + local storage."""
    alerts = _load_alerts()
    alerts = [a for a in alerts if a["id"] != alert_id]
    _save_alerts(alerts)


def check_price_alert(ticker: str, current_price: float, alert: Dict[str, Any]) -> bool:
    """
    Check if price alert condition is met.
    """
    if alert.get("type") != "price":
        return False
    
    condition = alert.get("condition")
    target_price = alert.get("target_price")
    
    if condition == "above" and current_price > target_price:
        return True
    elif condition == "below" and current_price < target_price:
        return True
    elif condition == "crosses_above" and current_price > target_price:
        # Would need to track previous price to detect crossing
        return True
    elif condition == "crosses_below" and current_price < target_price:
        return True
    
    return False


def check_volume_alert(ticker: str, current_volume: float, avg_volume: float, alert: Dict[str, Any]) -> bool:
    """
    Check if volume alert condition is met.
    """
    if alert.get("type") != "volume":
        return False
    
    multiplier = alert.get("multiplier", 2.0)
    
    if current_volume > avg_volume * multiplier:
        return True
    
    return False


def check_pattern_alert(ticker: str, patterns: List[Dict[str, Any]], alert: Dict[str, Any]) -> bool:
    """
    Check if pattern alert condition is met.
    """
    if alert.get("type") != "pattern":
        return False
    
    pattern_type = alert.get("pattern_type")
    min_confidence = alert.get("min_confidence", 70)
    
    for pattern in patterns:
        if pattern["type"] == pattern_type and pattern["confidence"] >= min_confidence:
            return True
    
    return False


def format_alert_message(alert: Dict[str, Any], ticker: str, current_price: float = None) -> str:
    """
    Format alert message for notification.
    """
    alert_type = alert.get("type")
    
    if alert_type == "price":
        condition = alert.get("condition")
        target = alert.get("target_price")
        return f"🚨 {ticker} PRICE ALERT!\n\nPrice {condition} ${target:.2f}\nCurrent: ${current_price:.2f}"
    
    elif alert_type == "volume":
        multiplier = alert.get("multiplier")
        return f"🚨 {ticker} VOLUME SURGE!\n\nVolume {multiplier}x average\nCheck for breakout!"
    
    elif alert_type == "pattern":
        pattern_type = alert.get("pattern_type")
        return f"🚨 {ticker} PATTERN ALERT!\n\n{pattern_type} detected\nCheck analyzer for details"
    
    elif alert_type == "news":
        sentiment = alert.get("sentiment")
        return f"🚨 {ticker} NEWS ALERT!\n\n{sentiment} news detected\nCheck news feed"
    
    return f"🚨 {ticker} ALERT!"


def format_alert_html(alert: Dict[str, Any], ticker: str, current_price: float = None) -> str:
    """
    Format alert as HTML email.
    """
    alert_type = alert.get("type")
    
    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; padding: 20px;">
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; border-radius: 10px; color: white;">
            <h2 style="margin: 0;">🚨 SwingFinder Alert</h2>
            <h1 style="margin: 10px 0;">{ticker}</h1>
        </div>
        
        <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; margin-top: 20px;">
    """
    
    if alert_type == "price":
        condition = alert.get("condition")
        target = alert.get("target_price")
        html += f"""
            <h3>Price Alert Triggered</h3>
            <p><strong>Condition:</strong> {condition} ${target:.2f}</p>
            <p><strong>Current Price:</strong> ${current_price:.2f}</p>
        """
    
    elif alert_type == "volume":
        multiplier = alert.get("multiplier")
        html += f"""
            <h3>Volume Surge Detected</h3>
            <p><strong>Volume:</strong> {multiplier}x average</p>
            <p>Check for potential breakout!</p>
        """
    
    elif alert_type == "pattern":
        pattern_type = alert.get("pattern_type")
        html += f"""
            <h3>Chart Pattern Detected</h3>
            <p><strong>Pattern:</strong> {pattern_type}</p>
            <p>Check analyzer for entry details</p>
        """
    
    html += """
        </div>
        
        <div style="margin-top: 20px; padding: 20px; background: #fff3cd; border-radius: 10px;">
            <p style="margin: 0;"><strong>⚡ Action Required:</strong></p>
            <p style="margin: 5px 0 0 0;">Open SwingFinder to analyze this setup</p>
        </div>
        
        <div style="margin-top: 20px; text-align: center; color: #666;">
            <p>SwingFinder - Professional Swing Trading Platform</p>
        </div>
    </body>
    </html>
    """
    
    return html


def log_alert_trigger(alert_id: str, ticker: str, message: str):
    """
    Log when an alert is triggered.
    """
    log = load_json("data/alert_log.json", default=[])
    if not isinstance(log, list):
        log = []

    log.append({
        "alert_id": alert_id,
        "ticker": ticker,
        "message": message,
        "triggered_at": datetime.now().isoformat()
    })

    # Keep only last 100 entries
    log = log[-100:]

    save_json(log, "data/alert_log.json")  # Fixed: data first, then path


def get_alert_history(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Get alert trigger history.
    """
    log = load_json("data/alert_log.json", default=[])
    if not isinstance(log, list):
        return []
    return log[-limit:]


def send_premarket_alert(symbol: str, current_price: float, prev_close: float,
                         change_pct: float, setup_type: str = None, entry: float = None) -> bool:
    """
    Send pre-market gap alert to user's email.
    Perfect for morning checks before market open.
    """
    try:
        user_email = st.secrets.get("USER_EMAIL")
        if not user_email:
            return False

        gap_direction = "UP 🚀" if change_pct > 0 else "DOWN ⚠️"

        subject = f"🌅 Pre-Market Alert: {symbol} Gapping {gap_direction}"

        # Plain text body
        body = f"""SwingFinder Pre-Market Alert
Time: {datetime.now().strftime('%I:%M %p ET')}

Symbol: {symbol}
Current Price: ${current_price:.2f}
Previous Close: ${prev_close:.2f}
Change: {change_pct:+.2f}%

"""

        if setup_type and entry:
            body += f"""Your Setup: {setup_type}
Entry Point: ${entry:.2f}
Status: {'⚠️ Entry may need adjustment' if abs(change_pct) > 2 else '✅ Setup still valid'}

"""

        body += """Action: Open SwingFinder to review setup
Link: https://swing-finder-v2.streamlit.app

---
SwingFinder Alert System
"""

        # HTML body for better formatting
        html_body = f"""
<html>
<body style="font-family: Arial, sans-serif; padding: 20px; background-color: #f5f5f5;">
    <div style="max-width: 600px; margin: 0 auto; background-color: white; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">

        <div style="background: linear-gradient(135deg, {'#00cc00' if change_pct > 0 else '#cc0000'} 0%, {'#00aa00' if change_pct > 0 else '#aa0000'} 100%); padding: 20px; color: white;">
            <h2 style="margin: 0; font-size: 24px;">🌅 Pre-Market Alert</h2>
            <h1 style="margin: 10px 0 0 0; font-size: 32px;">{symbol}</h1>
        </div>

        <div style="padding: 20px;">
            <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 15px;">
                <p style="margin: 5px 0; color: #666;"><strong>Time:</strong> {datetime.now().strftime('%I:%M %p ET')}</p>
                <p style="margin: 5px 0;"><strong>Current Price:</strong> ${current_price:.2f}</p>
                <p style="margin: 5px 0;"><strong>Previous Close:</strong> ${prev_close:.2f}</p>
                <p style="margin: 5px 0; font-size: 20px; color: {'#00cc00' if change_pct > 0 else '#cc0000'};">
                    <strong>Change:</strong> {change_pct:+.2f}%
                </p>
            </div>

            {'<div style="background-color: #e3f2fd; padding: 15px; border-radius: 5px; margin-bottom: 15px; border-left: 4px solid #2196F3;">' +
             f'<p style="margin: 5px 0;"><strong>Your Setup:</strong> {setup_type}</p>' +
             f'<p style="margin: 5px 0;"><strong>Entry Point:</strong> ${entry:.2f}</p>' +
             f'<p style="margin: 5px 0;"><strong>Status:</strong> {"⚠️ Entry may need adjustment" if abs(change_pct) > 2 else "✅ Setup still valid"}</p>' +
             '</div>' if setup_type and entry else ''}

            <div style="text-align: center; margin-top: 20px;">
                <a href="https://swing-finder-v2.streamlit.app"
                   style="display: inline-block; background-color: #4CAF50; color: white; padding: 12px 30px;
                          text-decoration: none; border-radius: 5px; font-size: 16px; font-weight: bold;">
                    Open SwingFinder
                </a>
            </div>
        </div>

        <div style="background-color: #f8f9fa; padding: 15px; text-align: center; border-top: 1px solid #ddd;">
            <p style="margin: 0; color: #666; font-size: 12px;">SwingFinder Alert System</p>
        </div>
    </div>
</body>
</html>
"""

        success = send_email_alert(user_email, subject, body, html_body)

        if success:
            log_alert_trigger(f"premarket_{symbol}", symbol, f"Pre-market gap {change_pct:+.2f}%")

        return success

    except Exception as e:
        print(f"❌ Pre-market alert failed: {e}")
        return False


def send_breakout_alert(symbol: str, current_price: float, entry_price: float,
                        setup_type: str, stop: float, target: float,
                        volume_ratio: float = None, notes: str = None) -> bool:
    """
    Send breakout/entry triggered alert to user's email.
    Perfect for when you're away from the app during market hours.
    """
    try:
        user_email = st.secrets.get("USER_EMAIL")
        if not user_email:
            return False

        subject = f"🚨 ENTRY TRIGGERED: {symbol} @ ${current_price:.2f}"

        # Calculate risk/reward
        risk_pct = abs((entry_price - stop) / entry_price) * 100
        reward_pct = abs((target - entry_price) / entry_price) * 100
        rr_ratio = reward_pct / risk_pct if risk_pct > 0 else 0

        # Plain text body
        body = f"""SwingFinder Breakout Alert!
Time: {datetime.now().strftime('%I:%M %p ET')}

🚨 ENTRY POINT TRIGGERED 🚨

Symbol: {symbol}
Current Price: ${current_price:.2f}
Your Entry: ${entry_price:.2f} ✅

Setup: {setup_type}
Stop Loss: ${stop:.2f}
Target: ${target:.2f}

Risk: {risk_pct:.1f}%
Reward: {reward_pct:.1f}%
R:R Ratio: {rr_ratio:.2f}:1

"""

        if volume_ratio:
            body += f"Volume: {volume_ratio:.1f}x average\n\n"

        if notes:
            body += f"Notes: {notes}\n\n"

        body += """Action: Open SwingFinder to execute trade
Link: https://swing-finder-v2.streamlit.app

---
SwingFinder Alert System
"""

        # HTML body
        html_body = f"""
<html>
<body style="font-family: Arial, sans-serif; padding: 20px; background-color: #f5f5f5;">
    <div style="max-width: 600px; margin: 0 auto; background-color: white; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">

        <div style="background: linear-gradient(135deg, #ff6600 0%, #ff4400 100%); padding: 20px; color: white;">
            <h2 style="margin: 0; font-size: 24px;">🚨 ENTRY TRIGGERED</h2>
            <h1 style="margin: 10px 0 0 0; font-size: 32px;">{symbol}</h1>
        </div>

        <div style="padding: 20px;">
            <div style="background-color: #fff3cd; padding: 15px; border-radius: 5px; margin-bottom: 15px; border-left: 4px solid #ff6600;">
                <p style="margin: 5px 0; color: #666;"><strong>Time:</strong> {datetime.now().strftime('%I:%M %p ET')}</p>
                <p style="margin: 5px 0; font-size: 24px; color: #ff6600;">
                    <strong>Price: ${current_price:.2f}</strong>
                </p>
            </div>

            <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 15px;">
                <h3 style="margin: 0 0 10px 0; color: #333;">Trade Details</h3>
                <p style="margin: 5px 0;"><strong>Setup:</strong> {setup_type}</p>
                <p style="margin: 5px 0;"><strong>Entry:</strong> ${entry_price:.2f} ✅</p>
                <p style="margin: 5px 0;"><strong>Stop Loss:</strong> ${stop:.2f}</p>
                <p style="margin: 5px 0;"><strong>Target:</strong> ${target:.2f}</p>
                {'<p style="margin: 5px 0;"><strong>Volume:</strong> ' + f'{volume_ratio:.1f}x average</p>' if volume_ratio else ''}
                {'<p style="margin: 5px 0;"><strong>Notes:</strong> ' + notes + '</p>' if notes else ''}
            </div>

            <div style="background-color: #e8f5e9; padding: 15px; border-radius: 5px; margin-bottom: 15px; border-left: 4px solid #4CAF50;">
                <h3 style="margin: 0 0 10px 0; color: #333;">Risk/Reward Analysis</h3>
                <p style="margin: 5px 0;"><strong>Risk:</strong> {risk_pct:.1f}%</p>
                <p style="margin: 5px 0;"><strong>Reward:</strong> {reward_pct:.1f}%</p>
                <p style="margin: 5px 0; font-size: 20px; color: #00cc00;">
                    <strong>R:R Ratio:</strong> {rr_ratio:.2f}:1
                </p>
            </div>

            <div style="text-align: center; margin-top: 20px;">
                <a href="https://swing-finder-v2.streamlit.app"
                   style="display: inline-block; background-color: #ff6600; color: white; padding: 15px 40px;
                          text-decoration: none; border-radius: 5px; font-size: 18px; font-weight: bold;">
                    Open SwingFinder Now
                </a>
            </div>
        </div>

        <div style="background-color: #f8f9fa; padding: 15px; text-align: center; border-top: 1px solid #ddd;">
            <p style="margin: 0; color: #666; font-size: 12px;">SwingFinder Alert System</p>
        </div>
    </div>
</body>
</html>
"""

        success = send_email_alert(user_email, subject, body, html_body)

        if success:
            log_alert_trigger(f"breakout_{symbol}", symbol, f"Entry triggered @ ${current_price:.2f}")

        return success

    except Exception as e:
        print(f"❌ Breakout alert failed: {e}")
        return False


def send_daily_summary(watchlist_summary: List[Dict[str, Any]]) -> bool:
    """
    Send end-of-day summary of watchlist performance.
    Perfect for after-market review.
    """
    try:
        user_email = st.secrets.get("USER_EMAIL")
        if not user_email:
            return False

        subject = f"📊 Daily Summary - {datetime.now().strftime('%B %d, %Y')}"

        # Plain text body
        body = f"""SwingFinder Daily Summary
Date: {datetime.now().strftime('%B %d, %Y')}

WATCHLIST PERFORMANCE:

"""

        for stock in watchlist_summary:
            body += f"""
{stock['symbol']}: {stock['change_pct']:+.2f}%
  Price: ${stock['close']:.2f}
  Status: {stock['status']}
"""

        body += """
---
SwingFinder Alert System
"""

        # HTML body
        html_body = f"""
<html>
<body style="font-family: Arial, sans-serif; padding: 20px; background-color: #f5f5f5;">
    <div style="max-width: 600px; margin: 0 auto; background-color: white; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">

        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; color: white;">
            <h2 style="margin: 0; font-size: 24px;">📊 Daily Summary</h2>
            <p style="margin: 5px 0 0 0; font-size: 16px;">{datetime.now().strftime('%B %d, %Y')}</p>
        </div>

        <div style="padding: 20px;">
            <h3 style="margin: 0 0 15px 0; color: #333;">Watchlist Performance</h3>
"""

        for stock in watchlist_summary:
            color = '#00cc00' if stock['change_pct'] > 0 else '#cc0000'
            html_body += f"""
            <div style="background-color: #f8f9fa; padding: 12px; border-radius: 5px; margin-bottom: 10px; border-left: 4px solid {color};">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <strong style="font-size: 18px;">{stock['symbol']}</strong>
                        <p style="margin: 5px 0; color: #666;">{stock['status']}</p>
                    </div>
                    <div style="text-align: right;">
                        <p style="margin: 0; font-size: 18px; color: {color};">{stock['change_pct']:+.2f}%</p>
                        <p style="margin: 5px 0; color: #666;">${stock['close']:.2f}</p>
                    </div>
                </div>
            </div>
"""

        html_body += """
        </div>

        <div style="background-color: #f8f9fa; padding: 15px; text-align: center; border-top: 1px solid #ddd;">
            <p style="margin: 0; color: #666; font-size: 12px;">SwingFinder Alert System</p>
        </div>
    </div>
</body>
</html>
"""

        success = send_email_alert(user_email, subject, body, html_body)

        if success:
            log_alert_trigger("daily_summary", "WATCHLIST", "Daily summary sent")

        return success

    except Exception as e:
        print(f"❌ Daily summary failed: {e}")
        return False

