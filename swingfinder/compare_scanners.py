"""Compare what both scanners would return for specific tickers"""
import pandas as pd
import numpy as np
from utils.tiingo_api import tiingo_history
from utils.indicators import compute_indicators

# Load token
try:
    with open('.streamlit/secrets.toml', 'r') as f:
        for line in f:
            if 'TIINGO_TOKEN' in line or 'TIINGO_API_KEY' in line:
                token = line.split('=')[1].strip().strip('"')
                break
except:
    print("❌ Could not load token")
    exit(1)

# Test tickers that should appear
test_tickers = ["LYFT", "CSX", "BKR", "AAPL", "MSFT"]

# Sensitivity 3 thresholds (both scanners use same)
thresholds = {
    "breakout_rsi": 55,
    "breakout_band": 0.55,
    "pullback_rsi_max": 50,
    "pullback_band": 0.45
}

mode = "Both"  # Test with Both mode
price_min = 10.0
price_max = 60.0
min_volume = 1_000_000

print("🔍 Comparing Scanner Logic for Test Tickers")
print(f"Mode: {mode} | Sensitivity: 3 | Price: ${price_min}-${price_max} | Min Volume: {min_volume:,}\n")

for ticker in test_tickers:
    print(f"\n{'='*70}")
    print(f"Testing: {ticker}")
    print(f"{'='*70}")
    
    df = tiingo_history(ticker, token, 120)
    
    if df is None or df.empty or len(df) < 60:
        print(f"❌ Insufficient data")
        continue
    
    df = compute_indicators(df)
    last = df.iloc[-1]
    
    px = float(last["Close"])
    vol = float(last["Volume"])
    ema20 = float(last["EMA20"])
    ema50 = float(last["EMA50"])
    rsi = float(last["RSI14"])
    band = float(last["BandPos20"])
    
    print(f"Price: ${px:.2f} | Volume: {vol:,.0f} | RSI: {rsi:.1f} | Band: {band:.2f}")
    print(f"EMA20: ${ema20:.2f} | EMA50: ${ema50:.2f} | Trend: {'UP' if ema20 > ema50 else 'DOWN'}")
    
    # Check basic filters
    if px < price_min or px > price_max:
        print(f"❌ FILTERED OUT: Price outside range")
        continue
    if vol < min_volume:
        print(f"❌ FILTERED OUT: Volume too low")
        continue
    if ema20 <= ema50:
        print(f"❌ FILTERED OUT: Downtrend")
        continue
    
    # Check setup detection
    setup = None
    near_miss = False
    
    # Breakout check
    if mode in ["Breakout", "Both"] and rsi > thresholds["breakout_rsi"] and band > thresholds["breakout_band"]:
        setup = "Breakout"
        print(f"✅ BREAKOUT SETUP DETECTED")
    
    # Pullback check
    elif mode in ["Pullback", "Both"] and rsi < thresholds["pullback_rsi_max"] and band <= thresholds["pullback_band"] and px <= ema20:
        setup = "Pullback"
        print(f"✅ PULLBACK SETUP DETECTED")
    
    # Near miss check
    if not setup:
        if mode in ["Breakout", "Both"] and 40 <= rsi <= 67 and 0.35 <= band <= 0.70:
            near_miss = True
            print(f"🟡 NEAR MISS: Breakout proximity")
        elif mode in ["Pullback", "Both"] and 40 <= rsi <= 70 and 0.20 <= band <= 0.60:
            near_miss = True
            print(f"🟡 NEAR MISS: Pullback proximity")
    
    # Final verdict
    if setup:
        print(f"✅ SHOULD APPEAR IN: Confirmed Setups tab")
    elif near_miss:
        print(f"✅ SHOULD APPEAR IN: Near Misses tab")
    else:
        print(f"❌ FILTERED OUT: No setup or near-miss detected")

print(f"\n\n{'='*70}")
print("✅ Comparison complete!")
print(f"{'='*70}")

