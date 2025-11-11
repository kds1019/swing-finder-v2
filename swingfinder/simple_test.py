"""
Simple test without streamlit
"""

import requests
import os
from dotenv import load_dotenv

load_dotenv()
TIINGO_TOKEN = os.getenv("TIINGO_TOKEN", "")

ticker = "AAPL"
url = f"https://api.tiingo.com/tiingo/fundamentals/{ticker.lower()}/statements"
headers = {"Authorization": f"Token {TIINGO_TOKEN}"}

response = requests.get(url, headers=headers, timeout=10)
data = response.json()

if data and len(data) > 0:
    quarterly = data[0]
    statement_data = quarterly.get("statementData", {})
    
    # Convert to dicts
    income_statement = {item['dataCode']: item['value'] 
                       for item in statement_data.get('incomeStatement', [])}
    balance_sheet = {item['dataCode']: item['value'] 
                    for item in statement_data.get('balanceSheet', [])}
    
    # Extract metrics
    revenue = income_statement.get("revenue", 0) or 0
    net_income = income_statement.get("netIncComStock", 0) or 0
    equity = balance_sheet.get("equity", 1) or 1
    debt = balance_sheet.get("debt", 0) or 0
    assets_current = balance_sheet.get("assetsCurrent", 0) or 0
    liabilities_current = balance_sheet.get("liabilitiesCurrent", 1) or 1
    
    # Calculate ratios
    profit_margin = (net_income / revenue * 100) if revenue > 0 else 0
    roe = (net_income / equity * 100) if equity > 0 else 0
    debt_to_equity = (debt / equity) if equity > 0 else 0
    current_ratio = (assets_current / liabilities_current) if liabilities_current > 0 else 0
    
    print("=" * 60)
    print(f"FUNDAMENTALS FOR {ticker}")
    print("=" * 60)
    print()
    print(f"Revenue: ${revenue:,.0f}")
    print(f"Net Income: ${net_income:,.0f}")
    print(f"Equity: ${equity:,.0f}")
    print(f"Debt: ${debt:,.0f}")
    print()
    print(f"Profit Margin: {profit_margin:.1f}%")
    print(f"ROE: {roe:.1f}%")
    print(f"Debt/Equity: {debt_to_equity:.2f}")
    print(f"Current Ratio: {current_ratio:.2f}")
    print()
    print("✅ DATA EXTRACTION WORKS!")
    print()
    print("The Fundamentals Scanner should now work in the app!")
else:
    print("❌ No data received")

