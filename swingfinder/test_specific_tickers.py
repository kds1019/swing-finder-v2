"""Test why specific tickers (LYFT, CSX, BKR) are not showing in scanner"""
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

# Test tickers
test_tickers = ["LYFT", "CSX", "BKR"]

print("🔍 Testing why these tickers are filtered out...\n")

for ticker in test_tickers:
    print(f"\n{'='*60}")
    print(f"Testing: {ticker}")
    print(f"{'='*60}")
    
    # Fetch data
    df = tiingo_history(ticker, token, 120)
    
    if df is None or df.empty:
        print(f"❌ No data returned for {ticker}")
        continue
    
    if len(df) < 60:
        print(f"❌ Not enough data points: {len(df)}")
        continue
    
    # Compute indicators
    df = compute_indicators(df)
    last = df.iloc[-1]
    
    # Extract values
    px = float(last["Close"])
    vol = float(last["Volume"])
    ema20 = float(last["EMA20"])
    ema50 = float(last["EMA50"])
    rsi = float(last["RSI14"])
    band = float(last["BandPos20"])
    
    print(f"\n📊 Current Metrics:")
    print(f"  Price: ${px:.2f}")
    print(f"  Volume: {vol:,.0f}")
    print(f"  EMA20: ${ema20:.2f}")
    print(f"  EMA50: ${ema50:.2f}")
    print(f"  RSI14: {rsi:.1f}")
    print(f"  BandPos20: {band:.2f}")
    
    # Check filters (default scanner settings)
    price_min = 10.0
    price_max = 60.0
    min_volume = 1_000_000
    
    print(f"\n✅ Filter Checks:")
    
    # Price filter
    if px < price_min or px > price_max:
        print(f"  ❌ FAILED: Price ${px:.2f} outside range ${price_min}-${price_max}")
    else:
        print(f"  ✅ PASSED: Price ${px:.2f} in range ${price_min}-${price_max}")
    
    # Volume filter
    if vol < min_volume:
        print(f"  ❌ FAILED: Volume {vol:,.0f} below minimum {min_volume:,.0f}")
    else:
        print(f"  ✅ PASSED: Volume {vol:,.0f} above minimum {min_volume:,.0f}")
    
    # Trend filter
    if ema20 > ema50:
        print(f"  ✅ PASSED: Uptrend (EMA20 ${ema20:.2f} > EMA50 ${ema50:.2f})")
    else:
        print(f"  ❌ FAILED: Downtrend (EMA20 ${ema20:.2f} < EMA50 ${ema50:.2f})")
    
    # Setup detection (Sensitivity 3 - Balanced)
    print(f"\n🎯 Setup Detection (Sensitivity 3):")
    
    # Breakout criteria
    breakout_rsi = 55
    breakout_band = 0.55
    if ema20 > ema50 and rsi > breakout_rsi and band > breakout_band:
        print(f"  ✅ BREAKOUT SETUP DETECTED!")
        print(f"     RSI {rsi:.1f} > {breakout_rsi} ✓")
        print(f"     Band {band:.2f} > {breakout_band} ✓")
    else:
        print(f"  ❌ No Breakout Setup:")
        if ema20 <= ema50:
            print(f"     Downtrend (EMA20 < EMA50)")
        else:
            if rsi <= breakout_rsi:
                print(f"     RSI {rsi:.1f} ≤ {breakout_rsi} (needs > {breakout_rsi})")
            if band <= breakout_band:
                print(f"     Band {band:.2f} ≤ {breakout_band} (needs > {breakout_band})")
    
    # Pullback criteria
    pullback_rsi_max = 50
    pullback_band = 0.45
    if ema20 > ema50 and rsi < pullback_rsi_max and band <= pullback_band and px <= ema20:
        print(f"  ✅ PULLBACK SETUP DETECTED!")
        print(f"     RSI {rsi:.1f} < {pullback_rsi_max} ✓")
        print(f"     Band {band:.2f} ≤ {pullback_band} ✓")
        print(f"     Price ${px:.2f} ≤ EMA20 ${ema20:.2f} ✓")
    else:
        print(f"  ❌ No Pullback Setup:")
        if ema20 <= ema50:
            print(f"     Downtrend (EMA20 < EMA50)")
        else:
            if rsi >= pullback_rsi_max:
                print(f"     RSI {rsi:.1f} ≥ {pullback_rsi_max} (needs < {pullback_rsi_max})")
            if band > pullback_band:
                print(f"     Band {band:.2f} > {pullback_band} (needs ≤ {pullback_band})")
            if px > ema20:
                print(f"     Price ${px:.2f} > EMA20 ${ema20:.2f} (needs ≤ EMA20)")
    
    # Near miss detection
    print(f"\n🟡 Near Miss Detection:")
    if ema20 > ema50:
        if 40 <= rsi <= 67 and 0.35 <= band <= 0.70:
            print(f"  ✅ NEAR MISS: Breakout proximity")
            print(f"     RSI {rsi:.1f} in range [40-67] ✓")
            print(f"     Band {band:.2f} in range [0.35-0.70] ✓")
        elif 40 <= rsi <= 70 and 0.20 <= band <= 0.60:
            print(f"  ✅ NEAR MISS: Pullback proximity")
            print(f"     RSI {rsi:.1f} in range [40-70] ✓")
            print(f"     Band {band:.2f} in range [0.20-0.60] ✓")
        else:
            print(f"  ❌ No near miss detected")
            print(f"     RSI {rsi:.1f} outside near-miss ranges")
            print(f"     Band {band:.2f} outside near-miss ranges")
    else:
        print(f"  ❌ Downtrend - no near misses in downtrends")

print(f"\n\n{'='*60}")
print("✅ Test complete!")
print(f"{'='*60}")

