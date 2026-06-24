"""
Scanner Validation Test
Checks if scanner correctly identifies setups on known stocks
"""

import os
from utils.tiingo_api import tiingo_history, _get_tiingo_token
import pandas as pd

def calculate_expected_setup(symbol):
    """
    Calculate what the setup SHOULD be based on raw technical data.
    Returns: (setup_type, reason, technical_data)
    """
    token = _get_tiingo_token()
    df = tiingo_history(symbol, token, days=60)
    
    if df is None or df.empty:
        return (None, "No data available", {})
    
    # Calculate indicators
    last = df.iloc[-1]
    close = float(last['Close'])
    volume = float(last['Volume'])
    
    # RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    current_rsi = rsi.iloc[-1]
    
    # EMAs
    ema20 = df['Close'].ewm(span=20, adjust=False).mean().iloc[-1]
    ema50 = df['Close'].ewm(span=50, adjust=False).mean().iloc[-1]
    
    # Bollinger position
    sma20 = df['Close'].rolling(20).mean().iloc[-1]
    std20 = df['Close'].rolling(20).std().iloc[-1]
    lower = sma20 - (2 * std20)
    upper = sma20 + (2 * std20)
    band_position = (close - lower) / (upper - lower) if (upper - lower) > 0 else 0.5
    
    # Determine expected setup
    uptrend = ema20 > ema50
    
    technical_data = {
        'price': round(close, 2),
        'volume': int(volume),
        'rsi': round(current_rsi, 1),
        'ema20': round(ema20, 2),
        'ema50': round(ema50, 2),
        'band_position': round(band_position, 2),
        'uptrend': uptrend
    }
    
    # Apply scanner logic (Sensitivity 3 - default)
    if uptrend:
        # Breakout criteria (Sensitivity 3)
        if current_rsi >= 55 and band_position >= 0.55:
            return ("Breakout", "Uptrend + RSI ≥55 + Band ≥0.55", technical_data)
        else:
            return ("None", f"Uptrend but RSI {current_rsi:.1f} < 55 or Band {band_position:.2f} < 0.55", technical_data)
    else:
        # Pullback criteria (Sensitivity 3)
        if 35 <= current_rsi <= 50 and band_position <= 0.40 and close <= ema20:
            return ("Pullback", "Downtrend + RSI 35-50 + Low band + Price ≤ EMA20", technical_data)
        else:
            return ("None", f"Downtrend but doesn't meet pullback (RSI {current_rsi:.1f}, Band {band_position:.2f})", technical_data)


def run_validation_test():
    """
    Test scanner against known stocks
    """
    print("=" * 80)
    print("SCANNER VALIDATION TEST")
    print("=" * 80)
    print()
    
    # Test stocks (mix of expected breakouts, pullbacks, and none)
    test_stocks = [
        "AAPL",   # Large cap tech - likely breakout or none
        "NVDA",   # High momentum - likely breakout
        "INTC",   # Your reported issue
        "TSLA",   # High volatility
        "SPY",    # Market index
        "QQQ",    # Tech index
        "BAC",    # Your reported issue
        "MSFT",   # Large cap
        "AMD",    # Tech/momentum
        "META",   # Social media
    ]
    
    results = []
    
    for symbol in test_stocks:
        print(f"Testing {symbol}...")
        setup, reason, tech = calculate_expected_setup(symbol)
        
        results.append({
            'Symbol': symbol,
            'Expected Setup': setup,
            'Reason': reason,
            'Price': tech.get('price'),
            'RSI': tech.get('rsi'),
            'EMA20': tech.get('ema20'),
            'EMA50': tech.get('ema50'),
            'Band': tech.get('band_position'),
            'Trend': 'UP' if tech.get('uptrend') else 'DOWN'
        })
    
    print()
    print("=" * 80)
    print("VALIDATION RESULTS")
    print("=" * 80)
    print()
    
    # Print formatted table
    print(f"{'Symbol':<8} {'Setup':<12} {'Price':<8} {'RSI':<6} {'Trend':<6} {'Band':<6} {'Reason'}")
    print("-" * 100)
    
    for r in results:
        print(f"{r['Symbol']:<8} {r['Expected Setup']:<12} ${r['Price']:<7.2f} {r['RSI']:<6.1f} {r['Trend']:<6} {r['Band']:<6.2f} {r['Reason']}")
    
    print()
    print("=" * 80)
    print("INSTRUCTIONS:")
    print("=" * 80)
    print("1. Run Scanner with these settings:")
    print("   - Price: $10-$500")
    print("   - Volume: >500k")
    print("   - Sensitivity: 3")
    print("   - Debug: ON")
    print()
    print("2. Manually search for each symbol above in Scanner results")
    print()
    print("3. Compare Scanner results with Expected Setup:")
    print("   - If Scanner shows 'Breakout' but Expected is 'None' → FALSE POSITIVE")
    print("   - If Scanner shows 'None' but Expected is 'Breakout' → FALSE NEGATIVE (MISSING)")
    print("   - If they match → CORRECT")
    print()
    print("4. Report any mismatches to identify the bug")
    print("=" * 80)


if __name__ == "__main__":
    run_validation_test()
