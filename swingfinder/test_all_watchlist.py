"""
Test all watchlist stocks to see their fundamentals
"""

import requests
import os
from dotenv import load_dotenv

load_dotenv()
TIINGO_TOKEN = os.getenv("TIINGO_TOKEN", "")

tickers = ["AAPL", "GOOGL", "NVDA"]

print("=" * 70)
print("TESTING ALL WATCHLIST STOCKS")
print("=" * 70)
print()

for ticker in tickers:
    print(f"\n{'=' * 70}")
    print(f"TESTING: {ticker}")
    print('=' * 70)
    
    url = f"https://api.tiingo.com/tiingo/fundamentals/{ticker.lower()}/statements"
    headers = {"Authorization": f"Token {TIINGO_TOKEN}"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ ERROR: {response.status_code}")
            print(f"Response: {response.text[:200]}")
            continue
        
        data = response.json()
        
        if not data or len(data) == 0:
            print(f"❌ No data returned for {ticker}")
            continue
        
        print(f"✅ Got {len(data)} statements")
        
        # Get latest quarterly
        quarterly = data[0]
        statement_data = quarterly.get("statementData", {})
        
        if not statement_data:
            print(f"❌ No statementData for {ticker}")
            continue
        
        # Convert to dicts
        income_statement = {item['dataCode']: item['value'] 
                           for item in statement_data.get('incomeStatement', [])}
        balance_sheet = {item['dataCode']: item['value'] 
                        for item in statement_data.get('balanceSheet', [])}
        
        # Extract metrics
        revenue = income_statement.get("revenue", 0) or 0
        net_income = income_statement.get("netIncComStock", 0) or income_statement.get("netinc", 0) or 0
        equity = balance_sheet.get("equity", 0) or 0
        debt = balance_sheet.get("debt", 0) or 0
        assets_current = balance_sheet.get("assetsCurrent", 0) or 0
        liabilities_current = balance_sheet.get("liabilitiesCurrent", 0) or 0
        
        print()
        print(f"Revenue: ${revenue:,.0f}")
        print(f"Net Income: ${net_income:,.0f}")
        print(f"Equity: ${equity:,.0f}")
        print(f"Debt: ${debt:,.0f}")
        print(f"Current Assets: ${assets_current:,.0f}")
        print(f"Current Liabilities: ${liabilities_current:,.0f}")
        print()
        
        # Calculate ratios
        if revenue > 0:
            profit_margin = (net_income / revenue * 100)
            print(f"✅ Profit Margin: {profit_margin:.1f}%")
        else:
            profit_margin = 0
            print(f"❌ Profit Margin: Cannot calculate (no revenue)")
        
        if equity > 0:
            roe = (net_income / equity * 100)
            debt_to_equity = (debt / equity)
            print(f"✅ ROE: {roe:.1f}%")
            print(f"✅ Debt/Equity: {debt_to_equity:.2f}")
        else:
            roe = 0
            debt_to_equity = 0
            print(f"❌ ROE: Cannot calculate (no equity)")
            print(f"❌ Debt/Equity: Cannot calculate (no equity)")
        
        if liabilities_current > 0:
            current_ratio = (assets_current / liabilities_current)
            print(f"✅ Current Ratio: {current_ratio:.2f}")
        else:
            current_ratio = 0
            print(f"❌ Current Ratio: Cannot calculate (no current liabilities)")
        
        print()
        print("FILTER CHECK (Min Profit: 10%, Min ROE: 15%, Max Debt: 2.0, Min Current: 1.0):")
        
        passes = []
        fails = []
        
        if profit_margin >= 10:
            passes.append(f"✅ Profit Margin: {profit_margin:.1f}% >= 10%")
        else:
            fails.append(f"❌ Profit Margin: {profit_margin:.1f}% < 10%")
        
        if roe >= 15:
            passes.append(f"✅ ROE: {roe:.1f}% >= 15%")
        else:
            fails.append(f"❌ ROE: {roe:.1f}% < 15%")
        
        if debt_to_equity <= 2.0:
            passes.append(f"✅ Debt/Equity: {debt_to_equity:.2f} <= 2.0")
        else:
            fails.append(f"❌ Debt/Equity: {debt_to_equity:.2f} > 2.0")
        
        if current_ratio >= 1.0:
            passes.append(f"✅ Current Ratio: {current_ratio:.2f} >= 1.0")
        else:
            fails.append(f"❌ Current Ratio: {current_ratio:.2f} < 1.0")
        
        for p in passes:
            print(p)
        for f in fails:
            print(f)
        
        if len(fails) == 0:
            print()
            print(f"🎉 {ticker} PASSES ALL FILTERS!")
        else:
            print()
            print(f"⚠️ {ticker} FAILS {len(fails)} filter(s)")
        
    except Exception as e:
        print(f"❌ EXCEPTION: {e}")

print()
print("=" * 70)
print("TEST COMPLETE!")
print("=" * 70)

