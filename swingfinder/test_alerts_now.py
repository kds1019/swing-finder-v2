"""
Test your alerts RIGHT NOW to see if they would trigger
"""

import json
import os

# Load Tiingo token the same way as the app
try:
    with open('.streamlit/secrets.toml', 'r') as f:
        for line in f:
            if 'TIINGO_TOKEN' in line or 'TIINGO_API_KEY' in line:
                token = line.split('=')[1].strip().strip('"')
                os.environ['TIINGO_API_KEY'] = token
                print(f"✅ Loaded Tiingo API key from secrets.toml\n")
                break
except Exception as e:
    print(f"⚠️ Could not load token from secrets.toml: {e}\n")

from check_alerts import (
    get_historical_data, check_indicator_alert, check_ema_cross_alert,
    check_macd_signal_alert, get_current_price
)

def test_volume_alert(ticker, data, multiplier):
    """Check if volume is above average by multiplier"""
    if not data:
        return False, "No data"
    
    current_vol = data.get("volume")
    prev_vol = data.get("volume_prev")
    
    if not current_vol or not prev_vol:
        return False, "Missing volume data"
    
    # Simple check: current volume vs previous day
    if current_vol > prev_vol * multiplier:
        return True, f"Volume {current_vol:,.0f} is {current_vol/prev_vol:.1f}x previous day ({prev_vol:,.0f})"
    
    return False, f"Volume {current_vol:,.0f} is only {current_vol/prev_vol:.1f}x previous day (needs {multiplier}x)"


def main():
    print("🔔 Testing Your Alerts RIGHT NOW\n")
    print("="*70)
    
    # Load alerts
    with open("data/alerts.json", "r") as f:
        alerts = json.load(f)
    
    active_alerts = [a for a in alerts if a.get("active")]
    print(f"Found {len(active_alerts)} active alerts\n")
    
    for i, alert in enumerate(active_alerts, 1):
        ticker = alert.get("ticker", "").upper()
        alert_type = alert.get("type")
        
        print(f"\n{'='*70}")
        print(f"Alert #{i}: {ticker} ({alert_type})")
        print(f"{'='*70}")
        
        # Fetch data
        print(f"📊 Fetching data for {ticker}...")
        data = get_historical_data(ticker)
        
        if not data:
            print(f"❌ Could not fetch data for {ticker}")
            continue
        
        print(f"✅ Data fetched successfully")
        print(f"   Current Price: ${data['close']:.2f}")
        print(f"   RSI: {data['rsi14']:.1f}")
        print(f"   Volume: {data['volume']:,.0f}")
        
        # Check alert
        triggered = False
        message = ""
        
        if alert_type == "volume":
            multiplier = alert.get("multiplier", 2.0)
            triggered, message = test_volume_alert(ticker, data, multiplier)
            
        elif alert_type == "indicator":
            triggered = check_indicator_alert(ticker, data, alert)
            if triggered:
                message = f"{alert.get('indicator')} {alert.get('condition')} {alert.get('threshold')}"
            else:
                indicator = alert.get("indicator", "RSI14").lower().replace("14", "14").replace("20", "20")
                current = data.get(indicator, 0)
                message = f"{alert.get('indicator')} is {current:.2f} (needs {alert.get('condition')} {alert.get('threshold')})"
                
        elif alert_type == "ema_cross":
            triggered = check_ema_cross_alert(ticker, data, alert)
            if triggered:
                message = f"EMA20 crossed {'above' if alert.get('cross_type') == 'bullish' else 'below'} EMA50"
            else:
                message = f"EMA20 ({data['ema20']:.2f}) vs EMA50 ({data['ema50']:.2f}) - no cross yet"
                
        elif alert_type == "macd_signal":
            triggered = check_macd_signal_alert(ticker, data, alert)
            if triggered:
                message = f"MACD crossed {'above' if alert.get('cross_type') == 'bullish' else 'below'} signal line"
            else:
                message = f"MACD ({data['macd']:.4f}) vs Signal ({data['macd_signal']:.4f}) - no cross yet"
        
        # Show result
        if triggered:
            print(f"\n🚨 ALERT TRIGGERED!")
            print(f"   {message}")
            print(f"   📧 Would send email to: {alert.get('email')}")
        else:
            print(f"\n✅ No trigger")
            print(f"   {message}")
    
    print(f"\n{'='*70}")
    print("✅ Alert test complete!")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()

