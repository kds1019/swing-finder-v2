"""
INDEPENDENT Scanner Validation
Uses DIFFERENT logic than your scanner to validate results
Fetches from Tiingo, calculates manually, shows what SHOULD pass
"""

import os
from utils.tiingo_api import tiingo_history
import pandas as pd

# Simple, clear criteria (NOT using your scanner code)
CRITERIA = {
    'min_price': 10,
    'max_price': 200,
    'min_volume': 500000,
    'breakout_rsi_min': 55,
    'breakout_rsi_max': 70,
    'pullback_rsi_min': 35,
    'pullback_rsi_max': 50,
}

def independent_check(symbol):
    """
    Independently calculate if stock should pass - NO scanner code used!
    Returns: (passes, setup_type, details)
    """
    token = os.getenv("TIINGO_TOKEN")
    df = tiingo_history(symbol, token, days=60)
    
    if df is None or df.empty:
        return (False, "No Data", {})
    
    # Get latest data
    latest = df.iloc[-1]
    close = float(latest['Close'])
    volume = float(latest['Volume'])
    
    # MANUAL calculation of RSI (simple, clear)
    prices = df['Close']
    deltas = prices.diff()
    gains = deltas.where(deltas > 0, 0)
    losses = -deltas.where(deltas < 0, 0)
    
    avg_gain = gains.rolling(window=14).mean().iloc[-1]
    avg_loss = losses.rolling(window=14).mean().iloc[-1]
    
    if avg_loss == 0:
        rsi = 100
    else:
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
    
    # MANUAL calculation of EMAs (simple, clear)
    ema20 = prices.ewm(span=20, adjust=False).mean().iloc[-1]
    ema50 = prices.ewm(span=50, adjust=False).mean().iloc[-1]
    
    # MANUAL calculation of Bollinger Band position
    sma20 = prices.rolling(20).mean().iloc[-1]
    std20 = prices.rolling(20).std().iloc[-1]
    upper_band = sma20 + (2 * std20)
    lower_band = sma20 - (2 * std20)
    
    if (upper_band - lower_band) > 0:
        band_position = (close - lower_band) / (upper_band - lower_band)
    else:
        band_position = 0.5
    
    details = {
        'price': round(close, 2),
        'volume': int(volume),
        'rsi': round(rsi, 1),
        'ema20': round(ema20, 2),
        'ema50': round(ema50, 2),
        'band_pos': round(band_position, 2),
    }
    
    # SIMPLE, CLEAR FILTER LOGIC (no scanner code)
    
    # 1. Basic filters
    if close < CRITERIA['min_price']:
        return (False, f"Price too low (${close:.2f})", details)
    if close > CRITERIA['max_price']:
        return (False, f"Price too high (${close:.2f})", details)
    if volume < CRITERIA['min_volume']:
        return (False, f"Volume too low ({volume:,.0f})", details)
    
    # 2. Trend check
    uptrend = ema20 > ema50
    
    # 3. Setup determination (SIMPLE LOGIC)
    if uptrend:
        # BREAKOUT: Uptrend + RSI 55-70 + Band > 0.5
        if CRITERIA['breakout_rsi_min'] <= rsi <= CRITERIA['breakout_rsi_max']:
            if band_position > 0.5:
                return (True, "BREAKOUT", details)
            else:
                return (False, f"Uptrend + RSI good but band too low ({band_position:.2f})", details)
        else:
            return (False, f"Uptrend but RSI {rsi:.1f} not in breakout range (55-70)", details)
    else:
        # PULLBACK: Downtrend + RSI 35-50 + Band < 0.4 + Price < EMA20
        if CRITERIA['pullback_rsi_min'] <= rsi <= CRITERIA['pullback_rsi_max']:
            if band_position < 0.4 and close < ema20:
                return (True, "PULLBACK", details)
            else:
                return (False, f"Downtrend + RSI good but band/price wrong", details)
        else:
            return (False, f"Downtrend but RSI {rsi:.1f} not in pullback range (35-50)", details)


def run_independent_check():
    """
    Run independent check on test stocks
    """
    print("="*100)
    print("INDEPENDENT SCANNER CHECK")
    print("Using DIFFERENT code than your scanner to validate results")
    print("="*100)
    print()
    
    # Test these specific stocks
    test_stocks = [
        "INTC",   # Your reported issue
        "BAC",    # Your reported issue  
        "AAPL", "NVDA", "TSLA", "MSFT", "AMD", "META",
        "SPY", "QQQ", "GOOGL", "AMZN", "NFLX", "DIS"
    ]
    
    results = []
    
    for symbol in test_stocks:
        print(f"Checking {symbol}...")
        passes, setup, details = independent_check(symbol)
        results.append({
            'Symbol': symbol,
            'Should Pass?': '✅ YES' if passes else '❌ NO',
            'Setup': setup,
            'Price': details.get('price', 0),
            'Volume': details.get('volume', 0),
            'RSI': details.get('rsi', 0),
            'EMA20>50': '✅' if details.get('ema20', 0) > details.get('ema50', 0) else '❌',
            'Band': details.get('band_pos', 0),
        })
    
    print()
    print("="*100)
    print("INDEPENDENT CHECK RESULTS (What SHOULD Pass)")
    print("="*100)
    print()
    
    # Show results
    print(f"{'Symbol':<8} {'Pass?':<10} {'Setup':<15} {'Price':<10} {'Volume':<12} {'RSI':<7} {'Trend':<8} {'Band':<7}")
    print("-"*100)
    
    should_pass = []
    for r in results:
        vol_str = f"{r['Volume']:,}" if r['Volume'] > 0 else 'N/A'
        print(f"{r['Symbol']:<8} {r['Should Pass?']:<10} {r['Setup']:<15} ${r['Price']:<9.2f} {vol_str:<12} {r['RSI']:<7.1f} {r['EMA20>50']:<8} {r['Band']:<7.2f}")
        if '✅' in r['Should Pass?']:
            should_pass.append(r['Symbol'])
    
    print()
    print("="*100)
    print(f"STOCKS THAT SHOULD PASS: {', '.join(should_pass) if should_pass else 'NONE'}")
    print("="*100)
    print()
    print("NOW RUN YOUR SCANNER AND COMPARE:")
    print("1. Do all these stocks appear in your scanner results?")
    print("2. If NO → Your scanner has a bug")
    print("3. If YES → Your scanner is working correctly")
    print()
    print("="*100)


if __name__ == "__main__":
    run_independent_check()
