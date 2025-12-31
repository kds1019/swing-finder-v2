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


def get_historical_data(ticker: str, days: int = 60) -> Dict[str, Any]:
    """Fetch historical data and calculate indicators."""
    try:
        import pandas as pd
        import numpy as np

        token = os.getenv("TIINGO_API_KEY")
        if not token:
            print(f"⚠️ TIINGO_API_KEY environment variable not set")
            # Try to load from .env file or config
            try:
                from dotenv import load_dotenv
                load_dotenv()
                token = os.getenv("TIINGO_API_KEY")
                if not token:
                    print(f"⚠️ Could not load TIINGO_API_KEY from .env file")
                    return None
            except:
                return None

        # Fetch historical data
        from datetime import timedelta
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

        url = f"https://api.tiingo.com/tiingo/daily/{ticker}/prices"
        headers = {"Authorization": f"Token {token}"}
        params = {"startDate": start_date}

        response = requests.get(url, headers=headers, params=params, timeout=15)

        if response.status_code != 200:
            return None

        data = response.json()
        if not data:
            return None

        df = pd.DataFrame(data)
        df['close'] = df['close'].astype(float)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)
        df['volume'] = df['volume'].astype(float)

        # Calculate indicators
        close = df['close']

        # EMA20 and EMA50
        ema20 = close.ewm(span=20, adjust=False).mean()
        ema50 = close.ewm(span=50, adjust=False).mean()

        # RSI14
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / (loss + 1e-9)
        rsi14 = 100 - (100 / (1 + rs))

        # ATR14
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - close.shift(1))
        low_close = np.abs(df['low'] - close.shift(1))
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr14 = tr.rolling(14).mean()

        # Bollinger Bands Position
        sma20 = close.rolling(20).mean()
        std20 = close.rolling(20).std()
        upper_band = sma20 + (2 * std20)
        lower_band = sma20 - (2 * std20)
        band_pos = (close - lower_band) / (upper_band - lower_band + 1e-9)

        # MACD
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd = ema12 - ema26
        macd_signal = macd.ewm(span=9, adjust=False).mean()

        # Return current and previous values for crossover detection
        return {
            "close": float(close.iloc[-1]),
            "close_prev": float(close.iloc[-2]) if len(close) > 1 else None,
            "ema20": float(ema20.iloc[-1]),
            "ema20_prev": float(ema20.iloc[-2]) if len(ema20) > 1 else None,
            "ema50": float(ema50.iloc[-1]),
            "ema50_prev": float(ema50.iloc[-2]) if len(ema50) > 1 else None,
            "rsi14": float(rsi14.iloc[-1]),
            "rsi14_prev": float(rsi14.iloc[-2]) if len(rsi14) > 1 else None,
            "atr14": float(atr14.iloc[-1]),
            "atr14_prev": float(atr14.iloc[-2]) if len(atr14) > 1 else None,
            "bandpos20": float(band_pos.iloc[-1]),
            "bandpos20_prev": float(band_pos.iloc[-2]) if len(band_pos) > 1 else None,
            "volume": float(df['volume'].iloc[-1]),
            "volume_prev": float(df['volume'].iloc[-2]) if len(df) > 1 else None,
            "macd": float(macd.iloc[-1]),
            "macd_prev": float(macd.iloc[-2]) if len(macd) > 1 else None,
            "macd_signal": float(macd_signal.iloc[-1]),
            "macd_signal_prev": float(macd_signal.iloc[-2]) if len(macd_signal) > 1 else None,
        }

    except Exception as e:
        import traceback
        print(f"Error fetching historical data for {ticker}: {e}")
        print(f"Traceback: {traceback.format_exc()}")
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


def check_indicator_alert(ticker: str, data: Dict[str, Any], alert: Dict[str, Any]) -> bool:
    """Check if indicator alert condition is met."""
    if alert.get("type") != "indicator":
        return False

    indicator = alert.get("indicator", "RSI14")
    condition = alert.get("condition")
    threshold = alert.get("threshold")

    # Map indicator names to data keys
    indicator_map = {
        "RSI14": "rsi14",
        "ATR14": "atr14",
        "BandPos20": "bandpos20",
        "Volume": "volume"
    }

    data_key = indicator_map.get(indicator)
    if not data_key or data_key not in data:
        return False

    current_value = data[data_key]
    prev_value = data.get(f"{data_key}_prev")

    if condition == "above":
        return current_value > threshold
    elif condition == "below":
        return current_value < threshold
    elif condition == "crosses_above":
        # Check if value crossed from below to above threshold
        if prev_value is not None:
            return prev_value <= threshold and current_value > threshold
    elif condition == "crosses_below":
        # Check if value crossed from above to below threshold
        if prev_value is not None:
            return prev_value >= threshold and current_value < threshold

    return False


def check_ema_cross_alert(ticker: str, data: Dict[str, Any], alert: Dict[str, Any]) -> bool:
    """Check if EMA crossover alert condition is met."""
    if alert.get("type") != "ema_cross":
        return False

    cross_type = alert.get("cross_type", "bullish")

    ema20 = data.get("ema20")
    ema20_prev = data.get("ema20_prev")
    ema50 = data.get("ema50")
    ema50_prev = data.get("ema50_prev")

    if None in [ema20, ema20_prev, ema50, ema50_prev]:
        return False

    if cross_type == "bullish":
        # EMA20 crosses above EMA50
        return ema20_prev <= ema50_prev and ema20 > ema50
    else:
        # EMA20 crosses below EMA50
        return ema20_prev >= ema50_prev and ema20 < ema50


def check_macd_signal_alert(ticker: str, data: Dict[str, Any], alert: Dict[str, Any]) -> bool:
    """Check if MACD signal alert condition is met."""
    if alert.get("type") != "macd_signal":
        return False

    cross_type = alert.get("cross_type", "bullish")

    macd = data.get("macd")
    macd_prev = data.get("macd_prev")
    macd_signal = data.get("macd_signal")
    macd_signal_prev = data.get("macd_signal_prev")

    if None in [macd, macd_prev, macd_signal, macd_signal_prev]:
        return False

    if cross_type == "bullish":
        # MACD crosses above signal line
        return macd_prev <= macd_signal_prev and macd > macd_signal
    else:
        # MACD crosses below signal line
        return macd_prev >= macd_signal_prev and macd < macd_signal


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

        triggered = False
        alert_message = ""

        if alert_type == "price":
            current_price = get_current_price(ticker)

            if current_price is None:
                print(f"⚠️ Could not fetch price for {ticker}")
                continue

            print(f"💰 Current price: ${current_price:.2f}")

            if check_price_alert(ticker, current_price, alert):
                triggered = True
                alert_message = f"{ticker} price alert triggered!\n\nCondition: {alert.get('condition')} ${alert.get('target_price'):.2f}\nCurrent: ${current_price:.2f}"

        elif alert_type in ["indicator", "ema_cross", "macd_signal"]:
            # Fetch historical data and indicators
            data = get_historical_data(ticker)

            if data is None:
                print(f"⚠️ Could not fetch data for {ticker}")
                continue

            # Check indicator alert
            if alert_type == "indicator":
                if check_indicator_alert(ticker, data, alert):
                    triggered = True
                    indicator = alert.get("indicator")
                    condition = alert.get("condition")
                    threshold = alert.get("threshold")
                    current_value = data.get(indicator.lower().replace("14", "14").replace("20", "20"))
                    alert_message = f"{ticker} {indicator} alert triggered!\n\n{indicator} {condition.replace('_', ' ')} {threshold}\nCurrent {indicator}: {current_value:.2f}"

            # Check EMA crossover alert
            elif alert_type == "ema_cross":
                if check_ema_cross_alert(ticker, data, alert):
                    triggered = True
                    cross_type = alert.get("cross_type")
                    alert_message = f"{ticker} EMA Crossover alert triggered!\n\n{'Bullish' if cross_type == 'bullish' else 'Bearish'} crossover detected\nEMA20: {data['ema20']:.2f}\nEMA50: {data['ema50']:.2f}"

            # Check MACD signal alert
            elif alert_type == "macd_signal":
                if check_macd_signal_alert(ticker, data, alert):
                    triggered = True
                    cross_type = alert.get("cross_type")
                    alert_message = f"{ticker} MACD Signal alert triggered!\n\n{'Bullish' if cross_type == 'bullish' else 'Bearish'} signal\nMACD: {data['macd']:.4f}\nSignal: {data['macd_signal']:.4f}"

        # Send notification if triggered
        if triggered:
            print(f"🚨 ALERT TRIGGERED for {ticker}!")
            triggered_count += 1

            email = alert.get("email")
            if email:
                subject = f"🚨 SwingFinder Alert: {ticker}"

                if send_email_alert(email, subject, alert_message, None):
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

