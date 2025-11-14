"""
Scheduled Alert Checker for GitHub Actions
Runs every 2 hours to check active alerts and send notifications
"""

import os
import json
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, Any, List


def load_alerts() -> List[Dict[str, Any]]:
    """Load active alerts from GitHub (using GitHub API to read from repo)."""
    try:
        # Get GitHub token and repo info from environment
        github_token = os.getenv("GITHUB_TOKEN")
        repo = os.getenv("GITHUB_REPOSITORY", "")  # Format: owner/repo
        
        if not github_token or not repo:
            print("⚠️ GitHub token or repo not found, trying local file...")
            # Fallback to local file for testing
            if os.path.exists("data/alerts.json"):
                with open("data/alerts.json", "r") as f:
                    alerts = json.load(f)
                return [a for a in alerts if a.get("active", False)]
            return []
        
        # Fetch alerts.json from GitHub repo
        url = f"https://api.github.com/repos/{repo}/contents/data/alerts.json"
        headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3.raw"
        }
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            alerts = response.json()
            return [a for a in alerts if a.get("active", False)]
        else:
            print(f"⚠️ Failed to fetch alerts from GitHub: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"❌ Error loading alerts: {e}")
        return []


def get_current_price(ticker: str) -> float:
    """Fetch current price from Tiingo."""
    try:
        token = os.getenv("TIINGO_API_KEY")
        if not token:
            print("❌ Tiingo API key not found")
            return None
        
        url = f"https://api.tiingo.com/tiingo/daily/{ticker}/prices"
        headers = {"Authorization": f"Token {token}"}
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data:
                return float(data[0]["close"])
        
        return None
        
    except Exception as e:
        print(f"❌ Error fetching price for {ticker}: {e}")
        return None


def check_price_alert(ticker: str, current_price: float, alert: Dict[str, Any]) -> bool:
    """Check if price alert condition is met."""
    if alert.get("type") != "price":
        return False
    
    condition = alert.get("condition")
    target_price = alert.get("target_price")
    
    if condition == "above" and current_price > target_price:
        return True
    elif condition == "below" and current_price < target_price:
        return True
    
    return False


def send_email_alert(to_email: str, subject: str, body: str, html_body: str = None) -> bool:
    """Send email alert using Gmail SMTP."""
    try:
        from_email = os.getenv("ALERT_EMAIL")
        app_password = os.getenv("ALERT_EMAIL_PASSWORD")
        
        if not from_email or not app_password:
            print("⚠️ Email credentials not configured")
            return False
        
        msg = MIMEMultipart('alternative')
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = subject
        
        part1 = MIMEText(body, 'plain')
        msg.attach(part1)
        
        if html_body:
            part2 = MIMEText(html_body, 'html')
            msg.attach(part2)
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(from_email, app_password)
            server.send_message(msg)
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return False


def format_alert_html(alert: Dict[str, Any], ticker: str, current_price: float) -> str:
    """Format alert as HTML email."""
    condition = alert.get("condition", "")
    target = alert.get("target_price", 0)
    
    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; padding: 20px;">
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; border-radius: 10px; color: white;">
            <h2 style="margin: 0;">🚨 SwingFinder Alert</h2>
            <h1 style="margin: 10px 0;">{ticker}</h1>
        </div>
        
        <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; margin-top: 20px;">
            <h3>Price Alert Triggered</h3>
            <p><strong>Condition:</strong> {condition} ${target:.2f}</p>
            <p><strong>Current Price:</strong> ${current_price:.2f}</p>
        </div>
        
        <div style="margin-top: 20px; padding: 20px; background: #fff3cd; border-radius: 10px;">
            <p style="margin: 0;"><strong>⚡ Action Required:</strong></p>
            <p style="margin: 5px 0 0 0;">Open SwingFinder to analyze this setup</p>
        </div>
    </body>
    </html>
    """
    
    return html


def main():
    """Main alert checking function."""
    print(f"🔔 Starting alert check at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Load active alerts
    alerts = load_alerts()
    print(f"📋 Found {len(alerts)} active alerts")
    
    if not alerts:
        print("✅ No active alerts to check")
        return
    
    # Check each alert
    triggered_count = 0
    
    for alert in alerts:
        ticker = alert.get("ticker", "").upper()
        alert_type = alert.get("type")
        
        print(f"\n🔍 Checking {ticker} ({alert_type} alert)...")
        
        if alert_type == "price":
            current_price = get_current_price(ticker)
            
            if current_price is None:
                print(f"⚠️ Could not fetch price for {ticker}")
                continue
            
            print(f"💰 Current price: ${current_price:.2f}")
            
            if check_price_alert(ticker, current_price, alert):
                print(f"🚨 ALERT TRIGGERED for {ticker}!")
                triggered_count += 1
                
                # Send notification
                email = alert.get("email")
                if email:
                    subject = f"🚨 SwingFinder Alert: {ticker}"
                    body = f"{ticker} price alert triggered!\n\nCondition: {alert.get('condition')} ${alert.get('target_price'):.2f}\nCurrent: ${current_price:.2f}"
                    html = format_alert_html(alert, ticker, current_price)
                    
                    if send_email_alert(email, subject, body, html):
                        print(f"✅ Email sent to {email}")
                    else:
                        print(f"❌ Failed to send email")
            else:
                print(f"✅ No trigger for {ticker}")
    
    print(f"\n{'='*60}")
    print(f"✅ Alert check complete: {triggered_count} alerts triggered")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()

