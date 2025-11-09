"""
Alert System for SwingFinder
Email and SMS notifications for watchlist signals
"""

import smtplib
import streamlit as st
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, List
from datetime import datetime
import json
from utils.storage import load_json, save_json


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


def create_alert(alert_config: Dict[str, Any]) -> str:
    """
    Create a new alert and save to alerts.json.
    Returns alert ID.
    """
    alerts = load_json("data/alerts.json") or []
    
    # Generate alert ID
    alert_id = f"alert_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    alert = {
        "id": alert_id,
        "created_at": datetime.now().isoformat(),
        "active": True,
        **alert_config
    }
    
    alerts.append(alert)
    save_json("data/alerts.json", alerts)
    
    return alert_id


def get_active_alerts() -> List[Dict[str, Any]]:
    """Get all active alerts."""
    alerts = load_json("data/alerts.json") or []
    return [a for a in alerts if a.get("active", False)]


def deactivate_alert(alert_id: str):
    """Deactivate an alert."""
    alerts = load_json("data/alerts.json") or []
    
    for alert in alerts:
        if alert["id"] == alert_id:
            alert["active"] = False
    
    save_json("data/alerts.json", alerts)


def delete_alert(alert_id: str):
    """Delete an alert."""
    alerts = load_json("data/alerts.json") or []
    alerts = [a for a in alerts if a["id"] != alert_id]
    save_json("data/alerts.json", alerts)


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
    log = load_json("data/alert_log.json") or []
    
    log.append({
        "alert_id": alert_id,
        "ticker": ticker,
        "message": message,
        "triggered_at": datetime.now().isoformat()
    })
    
    # Keep only last 100 entries
    log = log[-100:]
    
    save_json("data/alert_log.json", log)


def get_alert_history(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Get alert trigger history.
    """
    log = load_json("data/alert_log.json") or []
    return log[-limit:]

