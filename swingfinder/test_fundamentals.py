"""
Test Tiingo Fundamentals API
"""

import streamlit as st
from utils.fundamentals import get_fundamentals, extract_key_metrics, calculate_fundamental_score

# Get token
TIINGO_TOKEN = st.secrets.get("TIINGO_TOKEN", "")

print("Testing Tiingo Fundamentals API...")
print(f"Token: {TIINGO_TOKEN[:10]}..." if TIINGO_TOKEN else "No token!")
print()

# Test with a known stock
test_ticker = "AAPL"
print(f"Testing with {test_ticker}...")
print()

fundamentals = get_fundamentals(test_ticker, TIINGO_TOKEN)

if fundamentals:
    print("✅ Fundamentals data received!")
    print(f"Type: {type(fundamentals)}")
    print(f"Keys: {fundamentals.keys()}")
    print()
    
    if fundamentals.get("quarterly"):
        print("✅ Quarterly data exists!")
        quarterly = fundamentals["quarterly"]
        print(f"Quarterly keys: {quarterly.keys()}")
        print(f"Revenue: {quarterly.get('revenue', 'N/A')}")
        print(f"Net Income: {quarterly.get('netIncome', 'N/A')}")
        print()
        
        # Test metrics extraction
        metrics = extract_key_metrics(fundamentals)
        print("✅ Metrics extracted!")
        print(f"Profit Margin: {metrics.get('profit_margin', 0):.1f}%")
        print(f"ROE: {metrics.get('roe', 0):.1f}%")
        print(f"Debt/Equity: {metrics.get('debt_to_equity', 0):.2f}")
        print()
        
        # Test score calculation
        score_data = calculate_fundamental_score(fundamentals)
        print("✅ Score calculated!")
        print(f"Score: {score_data['score']}/100")
        print(f"Grade: {score_data['grade']}")
        print()
    else:
        print("❌ No quarterly data!")
        print(f"Fundamentals content: {fundamentals}")
else:
    print("❌ No fundamentals data received!")
    print("This could mean:")
    print("1. API token is invalid")
    print("2. Ticker not found")
    print("3. API endpoint changed")
    print("4. Network issue")

print()
print("Test complete!")

