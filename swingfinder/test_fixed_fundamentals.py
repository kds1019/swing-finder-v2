"""
Test the fixed fundamentals functions
"""

import os
from dotenv import load_dotenv
from utils.fundamentals import get_fundamentals, extract_key_metrics, calculate_fundamental_score

load_dotenv()
TIINGO_TOKEN = os.getenv("TIINGO_TOKEN", "")

print("Testing fixed fundamentals functions...")
print()

ticker = "AAPL"
print(f"Getting fundamentals for {ticker}...")

fundamentals = get_fundamentals(ticker, TIINGO_TOKEN)

if fundamentals:
    print("✅ Got fundamentals!")
    print()
    
    # Test extract_key_metrics
    print("Extracting metrics...")
    metrics = extract_key_metrics(fundamentals)
    
    if metrics:
        print("✅ Metrics extracted!")
        print()
        print(f"Revenue: ${metrics.get('revenue', 0):,.0f}")
        print(f"Net Income: ${metrics.get('net_income', 0):,.0f}")
        print(f"Profit Margin: {metrics.get('profit_margin', 0):.1f}%")
        print(f"ROE: {metrics.get('roe', 0):.1f}%")
        print(f"Debt/Equity: {metrics.get('debt_to_equity', 0):.2f}")
        print(f"Current Ratio: {metrics.get('current_ratio', 0):.2f}")
        print()
        
        # Test calculate_fundamental_score
        print("Calculating score...")
        score_data = calculate_fundamental_score(fundamentals)
        
        print("✅ Score calculated!")
        print()
        print(f"Score: {score_data['score']}/100")
        print(f"Grade: {score_data['grade']}")
        print()
        print("Details:")
        for detail in score_data['details']:
            print(f"  {detail}")
        print()
        
        print("=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print()
        print("The Fundamentals Scanner should now work!")
        print("Try it in the app with AAPL in your watchlist.")
    else:
        print("❌ No metrics extracted!")
        print("Check the extract_key_metrics function")
else:
    print("❌ No fundamentals data!")
    print("Check the get_fundamentals function")

